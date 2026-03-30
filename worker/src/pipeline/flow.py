from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from prefect import flow, get_run_logger, task

from models import AlbumCandidate
from musicbrainz import search_releases
from pipeline.config import load_config
from pipeline.storage import build_s3_client, check_storage_health, put_json
from scoring import score_candidates
from tagging import write_basic_id3


@task(retries=2, retry_delay_seconds=5)
def fetch_steam_metadata(app_id: int) -> dict[str, Any]:
    # MVP placeholder: replace with real Steam API client in Phase 1.
    return {
        "app_id": app_id,
        "title_variants": [str(app_id)],
        "release_date": None,
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
def partial_acoustid_verify(files: list[str], threshold: float) -> float:
    # MVP placeholder: force fallback behavior until acoustid module is wired.
    if not files:
        return 0.0
    return max(0.0, threshold - 0.1)


@task
def full_acoustid_fallback(files: list[str]) -> dict[str, Any]:
    if not files:
        return {"resolved": False, "reason": "no_files"}
    return {
        "resolved": True,
        "album": "Unknown Album",
        "artist": "Unknown Artist",
        "title": Path(files[0]).stem,
    }


@task
def write_tags_task(files: list[str], resolved: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"updated": 0, "dry_run": True}

    updated = 0
    for f in files:
        write_basic_id3(
            file_path=f,
            album=str(resolved.get("album", "Unknown Album")),
            title=Path(f).stem,
            artist=str(resolved.get("artist", "Unknown Artist")),
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
    return {"bucket": cfg.storage.bucket, "key": key}


@flow(name="sst-worker-pipeline")
def sst_pipeline(app_id: int, files: list[str], config_path: str, dry_run: bool = False) -> dict[str, Any]:
    logger = get_run_logger()
    cfg = load_config(config_path)

    steam = fetch_steam_metadata(app_id)
    candidates = search_musicbrainz_task(steam["title_variants"])
    scored = score_candidates_task(candidates, files, steam.get("release_date"))

    partial_ratio = partial_acoustid_verify(files, threshold=cfg.acoustid.partial_match_threshold)
    if partial_ratio >= cfg.acoustid.partial_match_threshold and scored:
        resolved = {
            "resolved": True,
            "album": scored[0].title,
            "artist": "Unknown Artist",
            "title": Path(files[0]).stem if files else "unknown",
            "resolution": "partial",
        }
    else:
        logger.info("Partial verification did not pass, escalating to full AcoustID fallback")
        resolved = full_acoustid_fallback(files)
        resolved["resolution"] = "full_fallback"

    status = "success" if resolved.get("resolved") else "review"
    tag_result = write_tags_task(files, resolved, dry_run=dry_run)

    payload = {
        "app_id": app_id,
        "status": status,
        "resolved": resolved,
        "tag_result": tag_result,
        "candidate_count": len(scored),
    }
    storage_ref = persist_results(config_path, app_id, payload, status=status)
    payload["storage"] = storage_ref

    return payload
