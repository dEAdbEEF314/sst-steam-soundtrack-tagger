import os
from typing import Any

import requests


def identify_track(duration: int, fingerprint: str) -> dict[str, Any] | None:
    api_key = os.getenv("ACOUSTID_API_KEY")
    if not api_key:
        raise RuntimeError("ACOUSTID_API_KEY is not set")

    resp = requests.get(
        "https://api.acoustid.org/v2/lookup",
        params={
            "client": api_key,
            "duration": duration,
            "fingerprint": fingerprint,
            "meta": "recordings",
            "format": "json",
        },
        timeout=20,
    )
    resp.raise_for_status()
    result = resp.json()
    matches = result.get("results", []) if isinstance(result, dict) else []
    if not matches:
        return None
    return matches[0]


def extract_recording_title(match: dict[str, Any] | None) -> str | None:
    if not match:
        return None
    recordings = match.get("recordings") if isinstance(match, dict) else None
    if not recordings:
        return None
    first = recordings[0]
    title = first.get("title")
    return str(title) if title else None
