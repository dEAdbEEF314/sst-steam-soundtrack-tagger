"""共通設定 (Core Config) の定義"""
import os
from pydantic import BaseModel, Field

class LlmConfig(BaseModel):
    """LLM 関連設定"""
    provider: str = Field(default="ollama")
    model: str = Field(default="qwen2.5-coder:14b")
    api_key: str = Field(default="")
    base_url: str = Field(default="")  # 必須項目（環境変数 or YAML で指定）
    temperature: float = Field(default=0.1)

    @classmethod
    def from_yaml_dict(cls, raw: dict) -> "LlmConfig":
        return cls(
            provider=str(raw.get("provider", "ollama")),
            model=str(raw.get("model", "qwen2.5-coder:14b")),
            api_key=os.getenv("LLM_API_KEY", raw.get("api_key", "")),
            base_url=os.getenv("OLLAMA_BASE_URL", raw.get("base_url")),
            temperature=float(raw.get("temperature", 0.1)),
        )

class StorageConfig(BaseModel):
    """ストレージ関連設定"""
    provider: str = Field(default="s3_compatible")
    endpoint_url: str = Field(default="")  # 必須項目
    bucket: str = Field(default="sst")
    ingest_prefix: str = Field(default="ingest/")
    archive_prefix: str = Field(default="archive/")
    review_prefix: str = Field(default="review/")
    workspace_prefix: str = Field(default="workspace/")

    @classmethod
    def from_yaml_dict(cls, raw: dict) -> "StorageConfig":
        prefixes = raw.get("prefixes", {})
        return cls(
            provider=str(raw.get("provider", "s3_compatible")),
            endpoint_url=os.getenv("S3_ENDPOINT_URL", raw.get("endpoint_url")),
            bucket=os.getenv("S3_BUCKET", raw.get("bucket", "sst")),
            ingest_prefix=str(prefixes.get("ingest", "ingest/")),
            archive_prefix=str(prefixes.get("archive", "archive/")),
            review_prefix=str(prefixes.get("review", "review/")),
            workspace_prefix=str(prefixes.get("workspace", "workspace/")),
        )

class ModeConfig(BaseModel):
    """動作環境設定"""
    dry_run: bool = Field(default=False)

    @classmethod
    def from_yaml_dict(cls, raw: dict) -> "ModeConfig":
        return cls(
            dry_run=bool(raw.get("dry_run", False))
        )
