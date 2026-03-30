import os
from dataclasses import dataclass

import yaml

from models import StorageConfig


@dataclass(slots=True)
class RetryConfig:
    max_attempts: int
    base_delay_sec: int


@dataclass(slots=True)
class AcoustIdConfig:
    partial_verify_tracks: int
    partial_match_threshold: float


@dataclass(slots=True)
class WorkerConfig:
    retry: RetryConfig
    acoustid: AcoustIdConfig
    storage: StorageConfig


def load_config(config_path: str) -> WorkerConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    retry_raw = raw.get("retry", {})
    acoustid_raw = raw.get("acoustid", {})
    storage_raw = raw.get("storage", {})
    prefixes = storage_raw.get("prefixes", {})

    endpoint = os.getenv("S3_ENDPOINT_URL", storage_raw.get("endpoint_url", ""))
    bucket = os.getenv("S3_BUCKET", storage_raw.get("bucket", ""))

    return WorkerConfig(
        retry=RetryConfig(
            max_attempts=int(retry_raw.get("max_attempts", 3)),
            base_delay_sec=int(retry_raw.get("base_delay_sec", 5)),
        ),
        acoustid=AcoustIdConfig(
            partial_verify_tracks=int(acoustid_raw.get("partial_verify_tracks", 3)),
            partial_match_threshold=float(acoustid_raw.get("partial_match_threshold", 0.8)),
        ),
        storage=StorageConfig(
            endpoint_url=endpoint,
            bucket=bucket,
            ingest_prefix=str(prefixes.get("ingest", "ingest/")),
            archive_prefix=str(prefixes.get("archive", "archive/")),
            review_prefix=str(prefixes.get("review", "review/")),
            workspace_prefix=str(prefixes.get("workspace", "workspace/")),
        ),
    )
