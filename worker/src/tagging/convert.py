from __future__ import annotations

import subprocess
from pathlib import Path


LOSSLESS_EXTENSIONS: frozenset[str] = frozenset({".flac", ".wav", ".aif", ".aiff"})


def convert_lossless_to_aiff(file_path: str) -> str:
    """Convert a lossless audio file to AIFF and return the output path.

    Lossy or unsupported formats are returned as-is so callers can pass mixed inputs.
    """
    src = Path(file_path)
    suffix = src.suffix.lower()

    if suffix == ".aiff" or suffix == ".aif":
        return str(src)

    if suffix not in LOSSLESS_EXTENSIONS:
        return str(src)

    dst = src.with_suffix(".aiff")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-c:a",
        "pcm_s16be",
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg command not found") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"ffmpeg conversion failed: {stderr}") from exc

    return str(dst)


def convert_flac_to_aiff(file_path: str) -> str:
    """Backward-compatible wrapper for older call sites.

    Now uses the generalized lossless-to-AIFF conversion behavior.
    """
    return convert_lossless_to_aiff(file_path)
