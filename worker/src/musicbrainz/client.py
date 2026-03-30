from datetime import datetime
from typing import Any

import requests

from models import AlbumCandidate

USER_AGENT = "sst/0.1 (https://example.invalid)"


def _to_candidate(item: dict[str, Any]) -> AlbumCandidate:
    return AlbumCandidate(
        mbid=str(item.get("id", "")),
        title=str(item.get("title", "")),
        track_count=item.get("track-count"),
        release_date=item.get("date"),
    )


def search_releases(titles: list[str], limit: int = 5) -> list[AlbumCandidate]:
    seen: set[str] = set()
    candidates: list[AlbumCandidate] = []

    for title in titles:
        if not title:
            continue
        resp = requests.get(
            "https://musicbrainz.org/ws/2/release",
            params={"query": f'release:"{title}"', "fmt": "json", "limit": limit},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("releases", []):
            mbid = str(item.get("id", ""))
            if not mbid or mbid in seen:
                continue
            seen.add(mbid)
            candidates.append(_to_candidate(item))

    return candidates
