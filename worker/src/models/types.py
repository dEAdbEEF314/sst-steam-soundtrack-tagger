from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Track:
    path: str
    duration: float | None = None


@dataclass(slots=True)
class AlbumCandidate:
    mbid: str
    title: str
    track_count: int | None = None
    release_date: str | None = None
    score: float = 0.0


@dataclass(slots=True)
class StorageConfig:
    endpoint_url: str
    bucket: str
    ingest_prefix: str
    archive_prefix: str
    review_prefix: str
    workspace_prefix: str


@dataclass(slots=True)
class RunContext:
    app_id: int
    files: list[str]
    dry_run: bool = False
    steam_metadata: dict[str, Any] | None = None
