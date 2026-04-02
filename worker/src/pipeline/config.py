"""Worker パイプライン設定の読み込み。"""
import os

import yaml
from pydantic import BaseModel

from core.config import StorageConfig


class RetryConfig(BaseModel):
    """リトライ設定。"""
    max_attempts: int = 3
    base_delay_sec: int = 5
    backoff_strategy: str = "exponential"
    base_backoff_factor: int = 2
    acoustid_max_attempts: int = 3
    musicbrainz_max_attempts: int = 2


class AcoustIdConfig(BaseModel):
    """AcoustID 関連設定。"""
    api_url: str = "https://api.acoustid.org/v2/lookup"
    api_key: str = ""
    partial_verify_tracks: int = 3
    partial_match_threshold: float = 0.8
    full_fallback_min_match_ratio: float = 0.4
    score_gap: float = 0.05
    skip_acoustid_threshold: float = 0.9


class SteamConfig(BaseModel):
    """Steam API 関連設定。"""
    api_url: str = "https://store.steampowered.com/api/appdetails"


class MusicBrainzConfig(BaseModel):
    """MusicBrainz API 関連設定。"""
    app_name: str = "sst"
    app_version: str = "0.1"
    contact_url: str = "https://example.invalid"


class FormatConfig(BaseModel):
    """音声フォーマット変換設定。"""
    lossless_target: str = "aiff"
    max_sample_rate: int = 48000
    max_bit_depth: int = 24


class WorkerConfig(BaseModel):
    """Worker の統合設定。"""
    retry: RetryConfig
    acoustid: AcoustIdConfig
    storage: StorageConfig
    format: FormatConfig
    steam: SteamConfig
    musicbrainz: MusicBrainzConfig


def compute_backoff_delays(cfg: RetryConfig, attempts: int) -> list[int]:
    """指数バックオフの遅延時間リストを生成する。

    例: base_delay_sec=5, factor=2, attempts=3 → [5, 10, 20]
    """
    return [
        cfg.base_delay_sec * (cfg.base_backoff_factor ** i)
        for i in range(attempts)
    ]


def load_config(config_path: str) -> WorkerConfig:
    """config.yaml を読み込んで WorkerConfig を返す。"""
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    retry_raw = raw.get("retry", {})
    acoustid_raw = raw.get("acoustid", {})
    format_raw = raw.get("format", {})
    steam_raw = raw.get("steam", {})
    musicbrainz_raw = raw.get("musicbrainz", {})

    storage_cfg = StorageConfig.from_yaml_dict(raw.get("storage", {}))

    return WorkerConfig(
        retry=RetryConfig(
            max_attempts=int(retry_raw.get("max_attempts", 3)),
            base_delay_sec=int(retry_raw.get("base_delay_sec", 5)),
            backoff_strategy=str(retry_raw.get("backoff_strategy", "exponential")),
            base_backoff_factor=int(retry_raw.get("base_backoff_factor", 2)),
            acoustid_max_attempts=int(retry_raw.get("acoustid_max_attempts", 3)),
            musicbrainz_max_attempts=int(retry_raw.get("musicbrainz_max_attempts", 2)),
        ),
        acoustid=AcoustIdConfig(
            api_url=str(acoustid_raw.get("api_url", "https://api.acoustid.org/v2/lookup")),
            api_key=str(os.getenv("ACOUSTID_API_KEY", acoustid_raw.get("api_key", ""))),
            partial_verify_tracks=int(acoustid_raw.get("partial_verify_tracks", 3)),
            partial_match_threshold=float(acoustid_raw.get("partial_match_threshold", 0.8)),
            full_fallback_min_match_ratio=float(acoustid_raw.get("full_fallback_min_match_ratio", 0.4)),
            score_gap=float(acoustid_raw.get("score_gap", 0.05)),
            skip_acoustid_threshold=float(acoustid_raw.get("skip_acoustid_threshold", 0.9)),
        ),
        storage=storage_cfg,
        format=FormatConfig(
            lossless_target=str(format_raw.get("lossless_target", "aiff")),
            max_sample_rate=int(format_raw.get("max_sample_rate", 48000)),
            max_bit_depth=int(format_raw.get("max_bit_depth", 24)),
        ),
        steam=SteamConfig(
            api_url=str(steam_raw.get("api_url", "https://store.steampowered.com/api/appdetails")),
        ),
        musicbrainz=MusicBrainzConfig(
            app_name=str(musicbrainz_raw.get("app_name", "sst")),
            app_version=str(musicbrainz_raw.get("app_version", "0.1")),
            contact_url=str(musicbrainz_raw.get("contact_url", "https://example.invalid")),
        ),
    )
