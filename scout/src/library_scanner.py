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


def _find_audio_files_by_ext(
    directory: str | Path,
    extensions: frozenset[str] | None = None,
) -> dict[str, list[str]]:
    """Recursively find audio files under *directory* and group them by extension.

    Returns a dict mapping lowercase extension → sorted list of absolute paths.
    """
    exts = extensions if extensions is not None else AUDIO_EXTENSIONS
    result: dict[str, list[str]] = {}
    
    for root, _dirs, files in os.walk(str(directory)):
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext in exts:
                full_path = os.path.join(root, fname)
                if ext not in result:
                    result[ext] = []
                result[ext].append(full_path)
    
    # Sort paths for each extension to ensure deterministic order
    for ext in result:
        result[ext].sort()
        
    return result


def _find_audio_files(
    directory: str | Path,
    extensions: frozenset[str] | None = None,
) -> list[str]:
    """Recursively find audio files under *directory*, sorted.
    (Maintained for backward compatibility)
    """
    by_ext = _find_audio_files_by_ext(directory, extensions)
    all_files = []
    for files in by_ext.values():
        all_files.extend(files)
    return sorted(all_files)


def _count_audio_files(directory: Path) -> int:
    """Count audio files recursively under *directory*."""
    return len(_find_audio_files(directory))


def _detect_format_subdirs(directory: Path) -> dict[str, Path]:
    """Detect format-named subdirectories under *directory*.

    Returns a dict mapping lowercase format keyword → subdirectory Path,
    for any subdirectory whose name contains a known audio format keyword
    AND which actually contains audio files.
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


def scan_library(
    library_path: str,
    *,
    audio_extensions: frozenset[str] | None = None,
    soundtrack_keywords: tuple[str, ...] | None = None,
) -> list[SteamApp]:
    """Scan *library_path* and return all installed soundtrack :class:`SteamApp` entries.

    Checks both ``steamapps/music/`` (preferred) and ``steamapps/common/``
    for each app's installdir.

    Args:
        library_path: Path to the Steam library root (contains ``steamapps/``).
        audio_extensions: Optional set of allowed audio extensions.
        soundtrack_keywords: Optional tuple of keywords to identify soundtracks.

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
    
    exts = audio_extensions or AUDIO_EXTENSIONS
    keywords = soundtrack_keywords or SOUNDTRACK_KEYWORDS

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
        # Check against keywords
        lower_name = name.lower()
        if not any(kw.lower() in lower_name for kw in keywords):
            logger.debug("Skipping (not a soundtrack by keywords): %s", name)
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

        # --- Audio file collection (All formats) ---
        audio_files_by_ext: dict[str, list[str]] = {}
        
        # Check for format-named subdirectories (flac/, mp3/, etc.)
        format_dirs = _detect_format_subdirs(install_path)
        
        if format_dirs:
            # If subdirs exist (e.g., flac/ and mp3/ are siblings), collect ALL of them.
            logger.debug("Format subdirs detected for %s: %s", name, list(format_dirs.keys()))
            for fmt_name, fmt_path in format_dirs.items():
                subdir_files = _find_audio_files_by_ext(fmt_path, extensions=exts)
                # Merge into results (one extension might appear in multiple subdirs, 
                # though unlikely in Steam layouts, we union them).
                for ext, paths in subdir_files.items():
                    if ext not in audio_files_by_ext:
                        audio_files_by_ext[ext] = []
                    audio_files_by_ext[ext].extend(paths)
        else:
            # No format subdirs; just scan everything under install_path.
            audio_files_by_ext = _find_audio_files_by_ext(install_path, extensions=exts)

        if not audio_files_by_ext:
            logger.debug("No audio files in %s — skipped", install_path)
            continue

        # For backward compatibility, pick the 'best' format_dir if possible
        best_format = _pick_best_format_dir(format_dirs)
        format_dir = best_format[1].name if best_format else None

        app = SteamApp(
            app_id=app_id,
            name=name,
            install_dir=install_dir_name,
            install_path=str(install_path),
            acf_path=str(acf_file),
            storage_location=location,
            format_dir=format_dir,
            audio_files_by_ext=audio_files_by_ext,
        )
        logger.info(
            "Found: %s  (app_id=%d, location=%s, total_tracks=%d, extensions=%s)",
            name, app_id, location, app.total_track_count, list(audio_files_by_ext.keys()),
        )
        results.append(app)

    return results


