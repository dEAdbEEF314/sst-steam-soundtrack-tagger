from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from prefect import flow, get_run_logger, task

from acoustid_api import extract_recording_title, identify_track
from fingerprint import generate_fingerprint
from models import AlbumCandidate
from musicbrainz import search_releases
from pipeline.config import load_config
from pipeline.storage import (
    build_s3_client,
    check_storage_health,
    put_json,
    put_json_for_prefix_name,
)
from scoring import score_candidates
from steam import fetch_steam_metadata as fetch_steam_metadata_client
from tagging import write_basic_id3


def choose_best_candidate_for_title(
    candidates: list[AlbumCandidate],
    fallback_title: str,
) -> AlbumCandidate | None:
    if not candidates:
        return None
    normalized = fallback_title.casefold().strip()

    def rank(candidate: AlbumCandidate) -> float:
        ratio = SequenceMatcher(None, candidate.title.casefold().strip(), normalized).ratio()
        return candidate.score + ratio

    return max(candidates, key=rank)


def refine_candidates_with_fallback_title(
    candidates: list[AlbumCandidate],
    fallback_title: str,
    files: list[str],
    steam_release_date: str | None,
) -> list[AlbumCandidate]:
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


@task(retries=2, retry_delay_seconds=5)
def fetch_steam_metadata(app_id: int) -> dict[str, Any]:
    try:
        return fetch_steam_metadata_client(app_id)
    except Exception:
        return {
            "app_id": app_id,
            "title_variants": [str(app_id)],
            "release_date": None,
            "steam_title": str(app_id),
        }


@task(retries=2, retry_delay_seconds=5)
def search_musicbrainz_task(title_variants: list[str]) -> list[AlbumCandidate]:
    return search_releases(title_variants)


@task
def score_candidates_task(
    candidates: list[AlbumCandidate],
    files: list[str],
    steam_release_date: str | None,
) -> list[AlbumCandidate]:
    return score_candidates(candidates, local_track_count=len(files), steam_release_date=steam_release_date)


@task
def partial_acoustid_verify(
    files: list[str],
    candidate_title: str,
    partial_tracks: int,
    threshold: float,
) -> float:
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
            match = identify_track(duration, fingerprint)
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
def full_acoustid_fallback(files: list[str]) -> dict[str, Any]:
    if not files:
        return {"resolved": False, "reason": "no_files"}

    titles: list[str] = []
    attempted = 0
    for file_path in files:
        try:
            duration, fingerprint = generate_fingerprint(file_path)
            match = identify_track(duration, fingerprint)
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
    if dry_run:
        return {"updated": 0, "dry_run": True}

    updated = 0
    total = len(files)
    for idx, f in enumerate(files, start=1):
        write_basic_id3(
            file_path=f,
            album=str(resolved.get("album", "Unknown Album")),
            title=Path(f).stem,
            artist=str(resolved.get("artist", "Unknown Artist")),
            track_number=idx,
            total_tracks=total,
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
    cfg = load_config(config_path)
    client = build_s3_client(cfg.storage)
    check_storage_health(client, cfg.storage)

    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    prefix = cfg.storage.archive_prefix if status == "success" else cfg.storage.review_prefix
    key = put_json(client, cfg.storage, prefix, f"app_{app_id}_{now}", result)

    # Keep lightweight execution metadata in workspace for debugging and replay.
    put_json_for_prefix_name(
        client,
        cfg.storage,
        "workspace",
        f"run_{app_id}_{now}",
        {"app_id": app_id, "status": status, "result_key": key},
    )

    # Record ingest references for auditability (source of processed files).
    file_refs = result.get("file_refs", [])
    put_json_for_prefix_name(
        client,
        cfg.storage,
        "ingest",
        f"refs_{app_id}_{now}",
        {"app_id": app_id, "files": file_refs},
    )
    return {"bucket": cfg.storage.bucket, "key": key}


@flow(name="sst-worker-pipeline")
def sst_pipeline(app_id: int, files: list[str], config_path: str, dry_run: bool = False) -> dict[str, Any]:
    logger = get_run_logger()
    cfg = load_config(config_path)

    retry_attempts = max(0, cfg.retry.max_attempts - 1)
    fetch_task = fetch_steam_metadata.with_options(
        retries=retry_attempts,
        retry_delay_seconds=cfg.retry.base_delay_sec,
    )
    search_task = search_musicbrainz_task.with_options(
        retries=retry_attempts,
        retry_delay_seconds=cfg.retry.base_delay_sec,
    )

    steam = fetch_task(app_id)
    candidates = search_task(steam["title_variants"])
    scored = score_candidates_task(candidates, files, steam.get("release_date"))
    final_candidates = scored

    best_title = scored[0].title if scored else steam.get("steam_title", str(app_id))

    partial_ratio = partial_acoustid_verify(
        files,
        candidate_title=best_title,
        partial_tracks=cfg.acoustid.partial_verify_tracks,
        threshold=cfg.acoustid.partial_match_threshold,
    )
    if partial_ratio >= cfg.acoustid.partial_match_threshold and scored:
        resolved = {
            "resolved": True,
            "album": scored[0].title,
            "artist": scored[0].artist or "Unknown Artist",
            "mbid": scored[0].mbid,
            "title": Path(files[0]).stem if files else "unknown",
            "resolution": "partial",
            "partial_ratio": partial_ratio,
        }
    else:
        logger.info("Partial verification did not pass, escalating to full AcoustID fallback")
        resolved = full_acoustid_fallback(files)
        resolved["resolution"] = "full_fallback"
        resolved["partial_ratio"] = partial_ratio
        if resolved.get("resolved"):
            if float(resolved.get("match_ratio", 0.0)) < cfg.acoustid.full_fallback_min_match_ratio:
                resolved["resolved"] = False
                resolved["reason"] = "low_confidence_full_fallback"
            else:
                final_candidates = refine_candidates_with_fallback_title(
                    scored,
                    fallback_title=str(resolved.get("title", "")),
                    files=files,
                    steam_release_date=steam.get("release_date"),
                )
                chosen = choose_best_candidate_for_title(final_candidates, str(resolved.get("title", "")))
                if chosen is not None:
                    resolved["album"] = chosen.title
                    resolved["artist"] = chosen.artist or "Unknown Artist"
                    resolved["mbid"] = chosen.mbid

    status = "success" if resolved.get("resolved") else "review"
    tag_result = write_tags_task(files, resolved, dry_run=dry_run)

    payload = {
        "app_id": app_id,
        "file_refs": files,
        "status": status,
        "resolved": resolved,
        "tag_result": tag_result,
        "candidate_count": len(final_candidates),
    }
    storage_ref = persist_results(config_path, app_id, payload, status=status)
    payload["storage"] = storage_ref

    return payload
