"""データモデル定義 (Pydantic BaseModel)."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PipelineState(str, Enum):
    """パイプラインの処理ステート。"""
    INGESTED = "INGESTED"
    FINGERPRINTED = "FINGERPRINTED"
    IDENTIFIED = "IDENTIFIED"
    ENRICHED = "ENRICHED"
    TAGGED = "TAGGED"
    STORED = "STORED"
    FAILED = "FAILED"


class Track(BaseModel):
    """音声ファイルのトラック情報。"""
    path: str
    duration: float | None = None


class AlbumCandidate(BaseModel):
    """MusicBrainz から取得したアルバム候補。"""
    mbid: str
    title: str
    artist: str | None = None
    track_count: int | None = None
    release_date: str | None = None
    score: float = 0.0


class ScoredCandidate(BaseModel):
    """スコアリング済みの候補。select_best_candidate で使用。"""
    candidate: AlbumCandidate
    final_score: float = 0.0


class RunContext(BaseModel):
    """パイプライン実行コンテキスト。"""
    app_id: int
    files: list[str]
    dry_run: bool = False
    steam_metadata: dict[str, Any] | None = None
