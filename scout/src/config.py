"""Scout アプリケーション設定の読み込み。"""
import yaml
from pydantic import BaseModel, Field

from core.config import LlmConfig, ModeConfig, StorageConfig


class PathsConfig(BaseModel):
    """ファイルパス関連設定。"""
    input_dir: str = Field(default="/mnt/work_area")

    @classmethod
    def from_yaml_dict(cls, raw: dict) -> "PathsConfig":
        return cls(
            input_dir=str(raw.get("input", "/mnt/work_area")),
        )


class ScanConfig(BaseModel):
    """スキャン関連設定。"""
    audio_extensions: list[str] = Field(
        default=[".flac", ".mp3", ".ogg", ".wav", ".m4a", ".aiff"]
    )
    soundtrack_keywords: list[str] = Field(
        default=["OST", "Soundtrack", "Sound Track", "Original Sound",
                 "Music Pack", "Digital Soundtrack", "Original Score"]
    )
    min_audio_files: int = Field(default=1)

    @classmethod
    def from_yaml_dict(cls, raw: dict) -> "ScanConfig":
        return cls(
            audio_extensions=list(raw.get("audio_extensions", [".flac", ".mp3", ".ogg", ".wav", ".m4a", ".aiff"])),
            soundtrack_keywords=list(raw.get("soundtrack_keywords", ["OST", "Soundtrack", "Sound Track", "Original Sound",
                                                                  "Music Pack", "Digital Soundtrack", "Original Score"])),
            min_audio_files=int(raw.get("min_audio_files", 1)),
        )


class VGMdbConfig(BaseModel):
    """VGMdb検索関連設定(Scout用)。"""
    cddb_url: str = Field(default="http://vgmdb.net:80/cddb/ja.utf8")

    @classmethod
    def from_yaml_dict(cls, raw: dict) -> "VGMdbConfig":
        return cls(
            cddb_url=str(raw.get("cddb_url", "http://vgmdb.net:80/cddb/ja.utf8"))
        )


class ScoutConfig(BaseModel):
    """Scout の統合設定。"""
    paths: PathsConfig
    scan: ScanConfig
    vgmdb: VGMdbConfig
    storage: StorageConfig
    llm: LlmConfig
    mode: ModeConfig


def load_config(config_path: str) -> ScoutConfig:
    """config.yaml を読み込んで ScoutConfig を返す。"""
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return ScoutConfig(
        paths=PathsConfig.from_yaml_dict(raw.get("paths", {})),
        scan=ScanConfig.from_yaml_dict(raw.get("scan", {})),
        vgmdb=VGMdbConfig.from_yaml_dict(raw.get("vgmdb", {})),
        storage=StorageConfig.from_yaml_dict(raw.get("storage", {})),
        llm=LlmConfig.from_yaml_dict(raw.get("llm", {})),
        mode=ModeConfig.from_yaml_dict(raw.get("mode", {})),
    )
