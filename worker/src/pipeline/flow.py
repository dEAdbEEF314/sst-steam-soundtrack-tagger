"""SST Worker パイプライン (Prefect Flow)。"""
from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from prefect import flow, get_run_logger, task

from acoustid_api import extract_recording_title, identify_track
from fingerprint import generate_fingerprint
from models import AlbumCandidate, PipelineState, ScoredCandidate
from musicbrainz import search_releases, init_client as init_mb_client
from pipeline.config import compute_backoff_delays, load_config
from pipeline.storage import (
    build_s3_client,
    check_storage_health,
    put_json,
    put_json_for_prefix_name,
)
from scoring import has_clear_winner, score_candidates
from steam import fetch_steam_metadata as fetch_steam_metadata_client
from tagging import write_tags


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------

def select_best_candidate(
    scored: list[ScoredCandidate],
) -> AlbumCandidate | None:
    """スコアリング済み候補リストから最良の候補を選択する。

    ドキュメント仕様に準拠したシグネチャ。
    候補が空なら None を返す。
    """
    if not scored:
        return None
    best = max(scored, key=lambda sc: sc.final_score)
    return best.candidate


def _to_scored_candidates(
    candidates: list[AlbumCandidate],
    fallback_title: str | None = None,
) -> list[ScoredCandidate]:
    """AlbumCandidate リストを ScoredCandidate リストに変換する。

    fallback_title が指定されている場合、タイトル類似度を加算して
    final_score を計算する。
    """
    result: list[ScoredCandidate] = []
    for c in candidates:
        bonus = 0.0
        if fallback_title:
            bonus = SequenceMatcher(
                None, c.title.casefold().strip(), fallback_title.casefold().strip()
            ).ratio()
        result.append(
            ScoredCandidate(candidate=c, final_score=c.score + bonus)
        )
    return result


def refine_candidates_with_fallback_title(
    candidates: list[AlbumCandidate],
    fallback_title: str,
    files: list[str],
    steam_release_date: str | None,
) -> list[AlbumCandidate]:
    """フォールバックタイトルで追加検索し、候補リストを拡充・再スコアリングする。"""
    if not fallback_title.strip():
        return candidates

    try:
        extra = search_releases([fallback_title], limit=7)
    except Exception:
        return candidates

    by_mbid: dict[str, AlbumCandidate] = {}
    for c in candidates:
        by_mbid[c.mbid] = c
    for c in extra:
        if c.mbid not in by_mbid:
            by_mbid[c.mbid] = c

    return score_candidates(
        list(by_mbid.values()),
        local_track_count=len(files),
        steam_release_date=steam_release_date,
    )


# ---------------------------------------------------------------------------
# Prefect タスク
# ---------------------------------------------------------------------------

@task(retries=2, retry_delay_seconds=5)
def fetch_steam_metadata(app_id: int, api_url: str) -> dict[str, Any]:
    """Steam Store API からメタデータを取得する。"""
    try:
        return fetch_steam_metadata_client(app_id, api_url=api_url)
    except Exception:
        return {
            "app_id": app_id,
            "title_variants": [str(app_id)],
            "release_date": None,
            "steam_title": str(app_id),
        }


@task(retries=1, retry_delay_seconds=5)
def search_musicbrainz_task(title_variants: list[str], app_name: str, app_version: str, contact_url: str) -> list[AlbumCandidate]:
    """MusicBrainz でリリース検索する。"""
    init_mb_client(app_name, app_version, contact_url)
    return search_releases(title_variants)


@task
def score_candidates_task(
    candidates: list[AlbumCandidate],
    files: list[str],
    steam_release_date: str | None,
) -> list[AlbumCandidate]:
    """候補にスコアを付与する。"""
    return score_candidates(candidates, local_track_count=len(files), steam_release_date=steam_release_date)


@task
def partial_acoustid_verify(
    files: list[str],
    candidate_title: str,
    partial_tracks: int,
    threshold: float,
    api_key: str,
    api_url: str,
) -> float:
    """先頭 N トラックで AcoustID 部分検証を行う。"""
    if not files or partial_tracks <= 0:
        return 0.0

    checks = files[:partial_tracks]
    matched = 0
    attempted = 0
    normalized_candidate = candidate_title.casefold().strip()
    title_similarity_threshold = max(0.5, threshold - 0.2)

    for file_path in checks:
        try:
            duration, fingerprint = generate_fingerprint(file_path)
            match = identify_track(duration, fingerprint, api_key=api_key, api_url=api_url)
            title = extract_recording_title(match)
            if not title:
                continue
            attempted += 1
            ratio = SequenceMatcher(None, normalized_candidate, title.casefold().strip()).ratio()
            if ratio >= title_similarity_threshold:
                matched += 1
        except Exception:
            continue

    if attempted == 0:
        return 0.0
    return matched / attempted


@task
def full_acoustid_fallback(files: list[str], api_key: str, api_url: str) -> dict[str, Any]:
    """全トラック AcoustID フォールバック。"""
    if not files:
        return {"resolved": False, "reason": "no_files"}

    titles: list[str] = []
    attempted = 0
    for file_path in files:
        try:
            duration, fingerprint = generate_fingerprint(file_path)
            match = identify_track(duration, fingerprint, api_key=api_key, api_url=api_url)
            title = extract_recording_title(match)
            attempted += 1
            if title:
                titles.append(title)
        except Exception:
            continue

    if not titles:
        return {"resolved": False, "reason": "acoustid_no_match"}

    representative = max(set(titles), key=titles.count)
    total_files = len(files)
    match_ratio = len(titles) / total_files if total_files > 0 else 0.0
    return {
        "resolved": True,
        "album": "Unknown Album",
        "artist": "Unknown Artist",
        "title": representative,
        "match_ratio": match_ratio,
        "attempted_tracks": attempted,
        "matched_tracks": len(titles),
    }


@task
def write_tags_task(files: list[str], resolved: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    """タグを書き込む。"""
    if dry_run:
        return {"updated": 0, "dry_run": True}

    updated = 0
    total = len(files)
    for idx, f in enumerate(files, start=1):
        write_tags(
            file_path=f,
            metadata={
                "album": str(resolved.get("album", "Unknown Album")),
                "title": Path(f).stem,
                "artist": str(resolved.get("artist", "Unknown Artist")),
                "track_number": idx,
                "total_tracks": total,
            },
        )
        updated += 1
    return {"updated": updated, "dry_run": False}


@task
def persist_results(
    config_path: str,
    app_id: int,
    result: dict[str, Any],
    status: str,
) -> dict[str, str]:
    """結果を SeaweedFS に永続化する。"""
    cfg = load_config(config_path)
    client = build_s3_client(cfg.storage)
    check_storage_health(client, cfg.storage)

    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    prefix = cfg.storage.archive_prefix if status == "success" else cfg.storage.review_prefix
    key = put_json(client, cfg.storage, prefix, f"app_{app_id}_{now}", result)

    # 実行メタデータを workspace に保存 (デバッグ・リプレイ用)
    put_json_for_prefix_name(
        client,
        cfg.storage,
        "workspace",
        f"run_{app_id}_{now}",
        {"app_id": app_id, "status": status, "result_key": key},
    )

    # ingest 参照情報を監査用に記録
    file_refs = result.get("file_refs", [])
    put_json_for_prefix_name(
        client,
        cfg.storage,
        "ingest",
        f"refs_{app_id}_{now}",
        {"app_id": app_id, "files": file_refs},
    )
    return {"bucket": cfg.storage.bucket, "key": key}


# ---------------------------------------------------------------------------
# メインフロー
# ---------------------------------------------------------------------------

@flow(name="sst-worker-pipeline")
def sst_pipeline(app_id: int, files: list[str], config_path: str, dry_run: bool = False) -> dict[str, Any]:
    """SST Worker パイプラインのメインフロー。"""
    logger = get_run_logger()
    cfg = load_config(config_path)
    state = PipelineState.INGESTED

    # --- タスク別リトライ設定 (config から読み込み、指数バックオフ適用) ---
    acoustid_retries = max(0, cfg.retry.acoustid_max_attempts - 1)
    mb_retries = max(0, cfg.retry.musicbrainz_max_attempts - 1)

    acoustid_delays = compute_backoff_delays(cfg.retry, acoustid_retries)
    mb_delays = compute_backoff_delays(cfg.retry, mb_retries)

    fetch_task = fetch_steam_metadata.with_options(
        retries=acoustid_retries,
        retry_delay_seconds=acoustid_delays or cfg.retry.base_delay_sec,
    )
    search_task = search_musicbrainz_task.with_options(
        retries=mb_retries,
        retry_delay_seconds=mb_delays or cfg.retry.base_delay_sec,
    )

    # --- Steam メタデータ取得 ---
    steam = fetch_task(app_id, api_url=cfg.steam.api_url)

    # --- MusicBrainz 検索 ---
    candidates = search_task(
        steam["title_variants"],
        app_name=cfg.musicbrainz.app_name,
        app_version=cfg.musicbrainz.app_version,
        contact_url=cfg.musicbrainz.contact_url,
    )
    scored = score_candidates_task(candidates, files, steam.get("release_date"))
    final_candidates = scored
    state = PipelineState.IDENTIFIED

    best_title = scored[0].title if scored else steam.get("steam_title", str(app_id))

    # --- score_gap チェック ---
    clear_winner = has_clear_winner(scored, cfg.acoustid.score_gap)
    if clear_winner and scored:
        logger.info("明確なスコア差あり (score_gap=%.2f)。部分検証でも高精度を期待。", cfg.acoustid.score_gap)

    # --- Fast-track (AcoustID スキップ) チェック ---
    if clear_winner and scored and scored[0].score >= cfg.acoustid.skip_acoustid_threshold:
        logger.info("✅ MusicBrainz スコアが閾値 (%.2f) 以上のため、AcoustID 検証をスキップします。", cfg.acoustid.skip_acoustid_threshold)
        best = scored[0]
        resolved = {
            "resolved": True,
            "album": best.title,
            "artist": best.artist or "Unknown Artist",
            "mbid": best.mbid,
            "title": Path(files[0]).stem if files else "unknown",
            "resolution": "fast_track",
            "partial_ratio": 1.0,
        }
        state = PipelineState.ENRICHED

    else:
        # --- 部分 AcoustID 検証 ---
        state = PipelineState.FINGERPRINTED
        partial_ratio = partial_acoustid_verify(
            files,
            candidate_title=best_title,
            partial_tracks=cfg.acoustid.partial_verify_tracks,
            threshold=cfg.acoustid.partial_match_threshold,
            api_key=cfg.acoustid.api_key,
            api_url=cfg.acoustid.api_url,
        )
        if partial_ratio >= cfg.acoustid.partial_match_threshold and scored:
            scored_list = _to_scored_candidates(scored)
            best = select_best_candidate(scored_list)
            resolved = {
                "resolved": True,
                "album": best.title if best else "Unknown Album",
                "artist": (best.artist if best else None) or "Unknown Artist",
                "mbid": best.mbid if best else "",
                "title": Path(files[0]).stem if files else "unknown",
                "resolution": "partial",
                "partial_ratio": partial_ratio,
            }
            state = PipelineState.ENRICHED
        else:
            logger.info("部分検証が閾値未満、全トラック AcoustID フォールバックに移行")
            resolved = full_acoustid_fallback(
                files,
                api_key=cfg.acoustid.api_key,
                api_url=cfg.acoustid.api_url,
            )
            resolved["resolution"] = "full_fallback"
            resolved["partial_ratio"] = partial_ratio
            if resolved.get("resolved"):
                if float(resolved.get("match_ratio", 0.0)) < cfg.acoustid.full_fallback_min_match_ratio:
                    resolved["resolved"] = False
                    resolved["reason"] = "low_confidence_full_fallback"
                    state = PipelineState.FAILED
                else:
                    final_candidates = refine_candidates_with_fallback_title(
                        scored,
                        fallback_title=str(resolved.get("title", "")),
                        files=files,
                        steam_release_date=steam.get("release_date"),
                    )
                    scored_list = _to_scored_candidates(
                        final_candidates,
                        fallback_title=str(resolved.get("title", "")),
                    )
                    chosen = select_best_candidate(scored_list)
                    if chosen is not None:
                        resolved["album"] = chosen.title
                        resolved["artist"] = chosen.artist or "Unknown Artist"
                        resolved["mbid"] = chosen.mbid
                    state = PipelineState.ENRICHED
            else:
                state = PipelineState.FAILED

    # --- タグ書き込み ---
    status = "success" if resolved.get("resolved") else "review"
    tag_result = write_tags_task(files, resolved, dry_run=dry_run)
    if resolved.get("resolved"):
        state = PipelineState.TAGGED

    # --- 結果永続化 ---
    payload = {
        "app_id": app_id,
        "file_refs": files,
        "status": status,
        "state": state.value,
        "resolved": resolved,
        "tag_result": tag_result,
        "candidate_count": len(final_candidates),
    }
    storage_ref = persist_results(config_path, app_id, payload, status=status)
    payload["storage"] = storage_ref
    if resolved.get("resolved"):
        state = PipelineState.STORED

    payload["state"] = state.value
    return payload
