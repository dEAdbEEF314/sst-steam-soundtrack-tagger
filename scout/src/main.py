"""Scout CLI entry point.

Scans a Steam library, identifies installed soundtrack apps, and uploads
their ACF manifests + audio files to SeaweedFS (S3-compatible).

Usage examples
--------------
# Dry-run: show what would be uploaded
python main.py --dry-run

# Upload a specific AppID only
python main.py --app-id 1234567

# Skip audio files (upload manifests only)
python main.py --no-audio
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from config import load_config as load_scout_config
from library_scanner import scan_library
from uploader import build_s3_client, check_storage_health, upload_app

# Load .env from the working directory (or /app/.env inside the container).
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("scout")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scout: upload Steam soundtracks to SeaweedFS"
    )
    p.add_argument(
        "--steam-library",
        metavar="PATH",
        help="Path to Steam library root (overrides STEAM_LIBRARY_PATH env)",
    )
    p.add_argument(
        "--app-id",
        type=int,
        metavar="ID",
        help="Process only this AppID",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be uploaded without touching S3",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Skip already-processed check and re-upload everything",
    )
    p.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Limit the number of new soundtracks to process",
    )
    p.add_argument(
        "--no-audio",
        action="store_true",
        help="Upload only ACF manifests, skip audio files",
    )
    p.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (overrides LOG_LEVEL env)",
    )
    p.add_argument(
        "--config",
        metavar="FILE",
        help="Path to config.yaml (default: /app/config.yaml)",
    )
    p.add_argument(
        "--output-json",
        metavar="FILE",
        help="Write run summary JSON to this file",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    
    # --- Setup Logging ---
    # CLI > ENV > Default
    log_level = args.log_level or os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True, # Ensure we override any existing config
    )
    logger.setLevel(log_level)

    # --- 設定ファイル読み込み ---
    from config import ScoutConfig, PathsConfig, VGMdbConfig, ScanConfig
    from core.config import StorageConfig, LlmConfig, ModeConfig

    config_path_val = args.config or os.getenv("SCOUT_CONFIG", "config.yaml")
    try:
        config = load_scout_config(config_path_val)
    except FileNotFoundError:
        logger.debug("Config file not found at %s — using defaults", config_path_val)
        config = ScoutConfig(
            paths=PathsConfig(),
            scan=ScanConfig(),
            vgmdb=VGMdbConfig(),
            storage=StorageConfig(),
            llm=LlmConfig(),
            mode=ModeConfig(),
        )

    # --- Resolve runtime parameters (CLI > env > config > default) ---
    steam_library: str | None = (
        args.steam_library
        or os.getenv("STEAM_LIBRARY_PATH")
        or config.paths.input_dir
    )
    if not steam_library:
        logger.error(
            "Steam library path not set. "
            "Use --steam-library, STEAM_LIBRARY_PATH env var, or config.yaml/paths/input_dir."
        )
        return 1

    endpoint_url: str = config.storage.endpoint_url
    bucket: str = config.storage.bucket
    dry_run: bool = args.dry_run or (os.getenv("DRY_RUN", "false").lower() == "true") or config.mode.dry_run
    upload_audio: bool = not args.no_audio

    logger.info("Steam library : %s", steam_library)
    logger.info("S3 endpoint   : %s", endpoint_url)
    logger.info("Bucket        : %s", bucket)
    logger.info("Dry-run       : %s", dry_run)
    logger.info("Upload audio  : %s", upload_audio)
    logger.info("Force upload  : %s", args.force)

    # --- Scan library ---
    from library_scanner import scan_library
    try:
        apps = scan_library(
            steam_library,
            audio_extensions=frozenset(config.scan.audio_extensions),
            soundtrack_keywords=tuple(config.scan.soundtrack_keywords),
        )
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    if not apps:
        logger.info("No soundtracks found in %s", steam_library)
        return 0

    if args.app_id is not None:
        apps = [a for a in apps if a.app_id == args.app_id]
        if not apps:
            logger.error("AppID %d not found in discovered soundtracks.", args.app_id)
            return 1

    # --- Build S3 client (only when not dry-run) ---
    s3 = None
    if not dry_run:
        from uploader import build_s3_client, check_storage_health, check_already_processed
        s3 = build_s3_client(endpoint_url)
        try:
            check_storage_health(s3, bucket)
        except Exception as exc:
            logger.error("Storage health check failed: %s", exc)
            return 1
    else:
        # In dry_run, we still want to check if it's already processed to show in logs
        from uploader import check_already_processed

    # --- Filter by process state and limit ---
    targets = []
    skipped_count = 0
    
    for app in apps:
        # If force is False, check if already uploaded
        # For dry_run, we check but logic continues for logging purposes unless specifically skipped
        if not args.force:
            # We need an s3 client for check_already_processed if not dry-run,
            # or a dummy/mock for dry-run if we want to simulate the check.
            # uploader.py's check_already_processed uses s3.head_object.
            # In dry_run we might not have a real s3 client.
            is_processed = False
            if s3:
                is_processed = check_already_processed(s3, bucket, app.app_id)
            
            if is_processed:
                logger.info("Skipping (already processed): %s (app_id=%d)", app.name, app.app_id)
                skipped_count += 1
                continue
        
        targets.append(app)

    # Apply limit
    if args.limit is not None and args.limit > 0:
        logger.info("Limit applied: processing first %d of %d candidates", args.limit, len(targets))
        targets = targets[:args.limit]

    logger.info("Soundtracks to process: %d (Skipped: %d)", len(targets), skipped_count)

    # --- Process each app ---
    results: list[dict] = []
    errors: list[dict] = []

    from uploader import upload_app
    for app in targets:
        logger.info(
            "Processing: %s  (app_id=%d, total_tracks=%d)",
            app.name,
            app.app_id,
            app.total_track_count,
        )
        try:
            result = upload_app(
                s3,
                bucket,
                app,
                dry_run=dry_run,
                upload_audio=upload_audio,
            )
            results.append(
                {
                    "app_id": result.app_id,
                    "name": result.name,
                    "acf_key": result.acf_key,
                    "file_count": len(result.file_keys),
                    "scout_result_key": result.scout_result_key,
                }
            )
        except Exception as exc:
            logger.error("Failed to upload %s (app_id=%d): %s", app.name, app.app_id, exc)
            errors.append({"app_id": app.app_id, "name": app.name, "error": str(exc)})

    summary = {
        "processed": len(results),
        "skipped": skipped_count,
        "failed": len(errors),
        "apps": results,
        "errors": errors,
    }
    logger.info("Done — processed=%d  skipped=%d  failed=%d", len(results), skipped_count, len(errors))

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Summary written: %s", args.output_json)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if errors else 0


    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Summary written: %s", args.output_json)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
