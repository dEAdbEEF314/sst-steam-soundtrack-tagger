"""Upload Steam soundtrack ACF + audio files to SeaweedFS (S3-compatible)."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config

from models import SteamApp, UploadResult

logger = logging.getLogger(__name__)

# Use multipart for files larger than 50 MB.
_MULTIPART_THRESHOLD = 50 * 1024 * 1024
_TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=_MULTIPART_THRESHOLD,
    max_concurrency=4,
)


def build_s3_client(endpoint_url: str):
    """Build a boto3 S3 client for SeaweedFS."""
    use_ssl = endpoint_url.startswith("https://")
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", ""),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", ""),
        region_name=os.getenv("S3_REGION", "us-east-1"),
        use_ssl=use_ssl,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def upload_app(
    s3,
    bucket: str,
    app: SteamApp,
    *,
    dry_run: bool = False,
    upload_audio: bool = True,
) -> UploadResult:
    """Upload ACF manifest and (optionally) audio files for *app* to S3.

    When *dry_run* is True, all S3 operations are skipped and only logged.
    The *s3* parameter may be ``None`` when *dry_run* is True.
    """
    acf_key = f"ingest/{app.app_id}/manifest.acf"
    file_keys: list[str] = []

    # --- Upload ACF manifest ---
    if dry_run:
        logger.info("[DRY-RUN] ACF  → s3://%s/%s", bucket, acf_key)
    else:
        _upload_file(s3, app.acf_path, bucket, acf_key, content_type="text/plain")
        logger.info("Uploaded ACF: %s", acf_key)

    # --- Upload audio files ---
    if upload_audio:
        for audio_path in app.audio_files:
            rel = Path(audio_path).relative_to(app.audio_root).as_posix()
            key = f"ingest/{app.app_id}/files/{rel}"
            if dry_run:
                size_mb = os.path.getsize(audio_path) / (1024 * 1024)
                logger.info(
                    "[DRY-RUN] Audio (%5.1f MB) → s3://%s/%s", size_mb, bucket, key
                )
            else:
                _upload_file(s3, audio_path, bucket, key)
                logger.info("Uploaded: %s", key)
            file_keys.append(key)

    # --- Write scout_result.json ---
    scout_result: dict = {
        "app_id": app.app_id,
        "name": app.name,
        "install_dir": app.install_dir,
        "storage_location": app.storage_location,
        "format_dir": app.format_dir,
        "track_count": len(app.audio_files),
        "acf_key": acf_key,
        "file_keys": file_keys,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
    }
    result_key = f"ingest/{app.app_id}/scout_result.json"
    body = json.dumps(scout_result, ensure_ascii=False).encode("utf-8")

    if dry_run:
        logger.info("[DRY-RUN] Result → s3://%s/%s", bucket, result_key)
        logger.info(
            "[DRY-RUN] Payload:\n%s",
            json.dumps(scout_result, ensure_ascii=False, indent=2),
        )
    else:
        s3.put_object(
            Bucket=bucket,
            Key=result_key,
            Body=body,
            ContentType="application/json",
        )
        logger.info("Scout result: %s", result_key)

    return UploadResult(
        app_id=app.app_id,
        name=app.name,
        acf_key=acf_key,
        file_keys=file_keys,
        scout_result_key=result_key,
        dry_run=dry_run,
    )


def check_storage_health(s3, bucket: str) -> None:
    """Raise if the target bucket is not reachable."""
    s3.head_bucket(Bucket=bucket)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _upload_file(
    s3,
    local_path: str,
    bucket: str,
    key: str,
    content_type: str = "application/octet-stream",
) -> None:
    s3.upload_file(
        local_path,
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
        Config=_TRANSFER_CONFIG,
    )
