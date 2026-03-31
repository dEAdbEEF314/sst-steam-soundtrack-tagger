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
# Config helpers
# ---------------------------------------------------------------------------

def _load_config(config_path: str | None) -> dict:
    path = config_path or os.getenv("SCOUT_CONFIG", "/app/config.yaml")
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        logger.debug("Config file not found at %s — using defaults", path)
        return {}


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
        "--no-audio",
        action="store_true",
        help="Upload only ACF manifests, skip audio files",
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
    config = _load_config(args.config)
    storage_cfg: dict = config.get("storage", {})

    # --- Resolve runtime parameters (CLI > env > config > default) ---
    steam_library: str | None = (
        args.steam_library
        or os.getenv("STEAM_LIBRARY_PATH")
        or config.get("scan", {}).get("steam_library_path")
    )
    if not steam_library:
        logger.error(
            "Steam library path not set. "
            "Use --steam-library, STEAM_LIBRARY_PATH env var, or config.yaml."
        )
        return 1

    endpoint_url: str = (
        os.getenv("S3_ENDPOINT_URL")
        or storage_cfg.get("endpoint_url", "http://swfs-s3.outergods.lan")
    )
    bucket: str = (
        os.getenv("S3_BUCKET")
        or storage_cfg.get("bucket", "buckets")
    )
    dry_run: bool = args.dry_run or os.getenv("DRY_RUN", "false").lower() == "true"
    upload_audio: bool = not args.no_audio

    logger.info("Steam library : %s", steam_library)
    logger.info("S3 endpoint   : %s", endpoint_url)
    logger.info("Bucket        : %s", bucket)
    logger.info("Dry-run       : %s", dry_run)
    logger.info("Upload audio  : %s", upload_audio)

    # --- Scan library ---
    try:
        apps = scan_library(steam_library)
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

    logger.info("Soundtracks to process: %d", len(apps))

    # --- Build S3 client (only when not dry-run) ---
    s3 = None
    if not dry_run:
        s3 = build_s3_client(endpoint_url)
        try:
            check_storage_health(s3, bucket)
        except Exception as exc:
            logger.error("Storage health check failed: %s", exc)
            return 1

    # --- Process each app ---
    results: list[dict] = []
    errors: list[dict] = []

    for app in apps:
        logger.info(
            "Processing: %s  (app_id=%d, tracks=%d)",
            app.name,
            app.app_id,
            len(app.audio_files),
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
        "failed": len(errors),
        "apps": results,
        "errors": errors,
    }
    logger.info("Done — processed=%d  failed=%d", len(results), len(errors))

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Summary written: %s", args.output_json)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
