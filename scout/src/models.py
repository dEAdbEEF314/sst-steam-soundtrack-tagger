"""Steam app data models for Scout."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# Where the installdir was found under steamapps/
StorageLocation = Literal["common", "music", "unknown"]

# Format priority used when multiple format subdirectories are present.
# Lower index = higher priority (prefer lossless).
FORMAT_PRIORITY: tuple[str, ...] = ("flac", "aiff", "wav", "ogg", "mp3", "m4a", "wma")


@dataclass
class SteamApp:
    """Represents an installed Steam soundtrack app."""

    app_id: int
    name: str
    install_dir: str        # relative dir name (value of installdir in ACF)
    install_path: str       # absolute path to root of installed depot
    acf_path: str           # absolute path to the .acf manifest
    storage_location: StorageLocation = "unknown"
    # When the depot uses format subdirectories (e.g. "flac" / "mp3" siblings),
    # this is the *selected* subdirectory name relative to install_path.
    # None means files live directly under install_path.
    # NOTE: In the new ingest flow, this mainly serves for backward compatibility
    # or as a reference to the 'best' format if needed.
    format_dir: str | None = None
    
    # New: Grouped by extension (e.g., {".flac": [path1, path2], ".mp3": [path3]})
    audio_files_by_ext: dict[str, list[str]] = field(default_factory=dict)

    @property
    def audio_files(self) -> list[str]:
        """全拡張子のファイルを統合したフラットリスト（後方互換用）。"""
        all_files = []
        for files in self.audio_files_by_ext.values():
            all_files.extend(files)
        return sorted(all_files)

    @property
    def total_track_count(self) -> int:
        """全拡張子の合計トラック数。"""
        return sum(len(files) for files in self.audio_files_by_ext.values())

    @property
    def audio_root(self) -> str:
        """Absolute path to the directory that contains audio files.
        If format_dir is set, returns that. Otherwise returns install_path.
        """
        if self.format_dir:
            from pathlib import Path
            return str(Path(self.install_path) / self.format_dir)
        return self.install_path


@dataclass
class UploadResult:
    """Result of uploading a single app to SeaweedFS."""

    app_id: int
    name: str
    acf_key: str
    file_keys: list[str]
    scout_result_key: str
    dry_run: bool = False

