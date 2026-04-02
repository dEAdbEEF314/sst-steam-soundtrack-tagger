"""AcoustID API クライアント (acoustid_api モジュール)。"""
import os
from typing import Any

import httpx


def identify_track(duration: int, fingerprint: str, api_key: str, api_url: str = "https://api.acoustid.org/v2/lookup") -> dict[str, Any] | None:
    """AcoustID API で音声トラックを識別する。"""
    if not api_key:
        raise RuntimeError("ACOUSTID_API_KEY is not set (provided as empty)")

    resp = httpx.get(
        api_url,
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
    """マッチ結果からレコーディングタイトルを抽出する。"""
    if not match:
        return None
    recordings = match.get("recordings") if isinstance(match, dict) else None
    if not recordings:
        return None
    first = recordings[0]
    title = first.get("title")
    return str(title) if title else None
