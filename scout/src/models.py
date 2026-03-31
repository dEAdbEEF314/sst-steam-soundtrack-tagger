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
    format_dir: str | None = None
    audio_files: list[str] = field(default_factory=list)

    @property
    def audio_root(self) -> str:
        """Absolute path to the directory that directly contains audio_files."""
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
