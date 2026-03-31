"""Scan a Steam library directory and find installed soundtrack apps."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from acf_parser import (
    get_app_id,
    get_install_dir,
    get_name,
    is_installed,
    parse_acf,
)
from models import FORMAT_PRIORITY, SteamApp, StorageLocation

# Re-export so inspect scripts can import directly from library_scanner
__all__ = [
    "FORMAT_PRIORITY",
    "AUDIO_EXTENSIONS",
    "SOUNDTRACK_KEYWORDS",
    "scan_library",
    "_detect_format_subdirs",
    "_find_audio_files",
    "_is_soundtrack_name",
    "_resolve_install_path",
]

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".flac", ".mp3", ".ogg", ".wav", ".m4a", ".aiff", ".wma"}
)

# Keywords that identify a Steam app as a soundtrack / music pack.
SOUNDTRACK_KEYWORDS: tuple[str, ...] = (
    "OST",
    "Soundtrack",
    "Sound Track",
    "Original Sound",
    "Music Pack",
    "Digital Soundtrack",
    "Original Score",
)


def _is_soundtrack_name(name: str) -> bool:
    """Return True if *name* contains a known soundtrack keyword."""
    lower = name.lower()
    return any(kw.lower() in lower for kw in SOUNDTRACK_KEYWORDS)


def _find_audio_files(
    directory: str | Path,
    extensions: frozenset[str] | None = None,
) -> list[str]:
    """Recursively find audio files under *directory*, sorted."""
    exts = extensions if extensions is not None else AUDIO_EXTENSIONS
    found: list[str] = []
    for root, _dirs, files in os.walk(str(directory)):
        for fname in files:
            if Path(fname).suffix.lower() in exts:
                found.append(os.path.join(root, fname))
    return sorted(found)


def _count_audio_files(directory: Path) -> int:
    """Count audio files recursively under *directory*."""
    count = 0
    for item in directory.rglob("*"):
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
            count += 1
    return count


def _detect_format_subdirs(directory: Path) -> dict[str, Path]:
    """Detect format-named subdirectories under *directory*.

    Returns a dict mapping lowercase format keyword → subdirectory Path,
    for any subdirectory whose name contains a known audio format keyword
    AND which actually contains audio files.

    Example:
        artofrally/
            art of rally OST - flac/   → {"flac": Path(...)}
            art of rally OST - mp3/    → {"mp3": Path(...)}
    """
    found: dict[str, Path] = {}
    counts: dict[str, int] = {}
    if not directory.is_dir():
        return found
    for subdir in directory.iterdir():
        if not subdir.is_dir():
            continue
        subdir_lower = subdir.name.lower()
        for fmt in FORMAT_PRIORITY:
            if fmt in subdir_lower:
                # Confirm at least one audio file exists (including nested layout).
                audio_count = _count_audio_files(subdir)
                if audio_count > 0:
                    # If the same format appears multiple times, keep the richest one.
                    prev = counts.get(fmt, -1)
                    if audio_count > prev:
                        found[fmt] = subdir
                        counts[fmt] = audio_count
                break  # only match the first format keyword per subdir
    return found


def _pick_best_format_dir(
    format_dirs: dict[str, Path],
) -> tuple[str, Path] | None:
    """Return (format_name, path) for the highest-priority format in *format_dirs*."""
    for fmt in FORMAT_PRIORITY:
        if fmt in format_dirs:
            return fmt, format_dirs[fmt]
    return None


def _resolve_install_path(
    steamapps_dir: Path,
    install_dir_name: str,
) -> tuple[Path, StorageLocation] | tuple[None, None]:
    """Locate the depot directory for *install_dir_name*.

    Checks in order:
      1. steamapps/music/
      2. steamapps/common/

    Returns (absolute_path, location) or (None, None) if not found.
    """
    for subdir, location in [("music", "music"), ("common", "common")]:
        candidate = steamapps_dir / subdir / install_dir_name
        if candidate.is_dir():
            return candidate, location  # type: ignore[return-value]
    return None, None


def scan_library(library_path: str) -> list[SteamApp]:
    """Scan *library_path* and return all installed soundtrack :class:`SteamApp` entries.

    Checks both ``steamapps/music/`` (preferred) and ``steamapps/common/``
    for each app's installdir.  When a ``music/`` depot contains format
    subdirectories (e.g. a ``flac`` subdir alongside a ``mp3`` subdir),
    the highest-priority lossless format is selected and only those files
    are returned.

    Args:
        library_path: Path to the Steam library root (contains ``steamapps/``).

    Raises:
        FileNotFoundError: If ``steamapps/`` does not exist under *library_path*.
    """
    root = Path(library_path)
    steamapps_dir = root / "steamapps"

    if not steamapps_dir.is_dir():
        raise FileNotFoundError(
            f"steamapps directory not found under: {library_path}"
        )

    results: list[SteamApp] = []

    for acf_file in sorted(steamapps_dir.glob("appmanifest_*.acf")):
        try:
            app_state = parse_acf(acf_file)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", acf_file.name, exc)
            continue

        if not is_installed(app_state):
            logger.debug("Skipping (not installed): %s", get_name(app_state))
            continue

        name = get_name(app_state)
        if not _is_soundtrack_name(name):
            logger.debug("Skipping (not a soundtrack): %s", name)
            continue

        app_id = get_app_id(app_state)
        if app_id is None:
            logger.warning("No valid appid in %s — skipped", acf_file.name)
            continue

        install_dir_name = get_install_dir(app_state)
        install_path, location = _resolve_install_path(steamapps_dir, install_dir_name)

        if install_path is None:
            logger.warning(
                "Install path not found (common/ nor music/): %s — skipped",
                install_dir_name,
            )
            continue

        # --- Format subdirectory detection ---
        format_dirs = _detect_format_subdirs(install_path)
        format_dir: str | None = None
        audio_dir = install_path

        if format_dirs:
            best = _pick_best_format_dir(format_dirs)
            if best:
                fmt_name, fmt_path = best
                format_dir = fmt_path.name
                audio_dir = fmt_path
                logger.debug(
                    "Format subdirs detected for %s; selected '%s' (%s)",
                    name, format_dir, fmt_name,
                )

        audio_files = _find_audio_files(audio_dir)
        if not audio_files:
            logger.debug("No audio files in %s — skipped", audio_dir)
            continue

        app = SteamApp(
            app_id=app_id,
            name=name,
            install_dir=install_dir_name,
            install_path=str(install_path),
            acf_path=str(acf_file),
            storage_location=location,
            format_dir=format_dir,
            audio_files=audio_files,
        )
        logger.info(
            "Found: %s  (app_id=%d, location=%s, tracks=%d, format_dir=%s)",
            name, app_id, location, len(audio_files), format_dir or "—",
        )
        results.append(app)

    return results

