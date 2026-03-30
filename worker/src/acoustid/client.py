import os
from typing import Any

import acoustid


def identify_track(duration: int, fingerprint: str) -> dict[str, Any] | None:
    api_key = os.getenv("ACOUSTID_API_KEY")
    if not api_key:
        raise RuntimeError("ACOUSTID_API_KEY is not set")

    result = acoustid.lookup(api_key, fingerprint, duration)
    matches = result.get("results", []) if isinstance(result, dict) else []
    if not matches:
        return None
    return matches[0]
