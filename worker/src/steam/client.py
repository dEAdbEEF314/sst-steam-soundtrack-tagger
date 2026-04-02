"""Steam Store API クライアント。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


def _normalize_date(text: str | None) -> str | None:
    """Steam の日付文字列を ISO 形式に正規化する。"""
    if not text:
        return None
    # Steam store date strings vary by locale; keep raw if strict parse fails.
    for fmt in ("%d %b, %Y", "%b %d, %Y", "%d %B, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def fetch_steam_metadata(app_id: int, api_url: str = "https://store.steampowered.com/api/appdetails") -> dict[str, Any]:
    """Steam Store API からアプリのメタデータを取得する。"""
    resp = httpx.get(api_url, params={"appids": app_id, "l": "english"}, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    item = payload.get(str(app_id), {})
    if not item.get("success"):
        return {"app_id": app_id, "title_variants": [str(app_id)], "release_date": None}

    data = item.get("data", {})
    name = str(data.get("name", "")).strip()
    release_date_raw = data.get("release_date", {}).get("date")

    variants = [name] if name else []
    if "-" in name:
        variants.extend(part.strip() for part in name.split("-") if part.strip())

    dedup: list[str] = []
    seen: set[str] = set()
    for title in variants:
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(title)

    if not dedup:
        dedup = [str(app_id)]

    return {
        "app_id": app_id,
        "title_variants": dedup,
        "release_date": _normalize_date(release_date_raw),
        "steam_title": name or str(app_id),
    }
