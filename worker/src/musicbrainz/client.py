"""MusicBrainz API クライアント (musicbrainzngs 使用)。"""
from __future__ import annotations

from typing import Any

import musicbrainzngs

from models import AlbumCandidate

# デフォルトの User-Agent 設定 (MusicBrainz API 利用規約で必須)
musicbrainzngs.set_useragent("sst", "0.1", "https://example.invalid")


def init_client(app_name: str, app_version: str, contact_url: str) -> None:
    """ConfigからUser-Agentを設定する。"""
    musicbrainzngs.set_useragent(app_name, app_version, contact_url)


def _extract_artist(item: dict[str, Any]) -> str | None:
    """リリース情報からアーティスト名を抽出する。"""
    artists = item.get("artist-credit", [])
    if not artists:
        return None
    names: list[str] = []
    for entry in artists:
        if isinstance(entry, str):
            names.append(entry)
            continue
        artist_obj = entry.get("artist") if isinstance(entry, dict) else None
        if isinstance(artist_obj, dict) and artist_obj.get("name"):
            names.append(str(artist_obj["name"]))
    joined = "".join(names).strip()
    return joined or None


def _to_candidate(item: dict[str, Any]) -> AlbumCandidate:
    """MusicBrainz のリリース情報を AlbumCandidate に変換する。"""
    return AlbumCandidate(
        mbid=str(item.get("id", "")),
        title=str(item.get("title", "")),
        artist=_extract_artist(item),
        track_count=item.get("medium-track-count") or item.get("track-count"),
        release_date=item.get("date"),
    )


def search_releases(titles: list[str], limit: int = 5) -> list[AlbumCandidate]:
    """複数タイトルで MusicBrainz をリリース検索し、MBID で重複排除して返す。"""
    seen: set[str] = set()
    candidates: list[AlbumCandidate] = []

    for title in titles:
        if not title:
            continue
        result = musicbrainzngs.search_releases(
            release=title,
            limit=limit,
        )
        for item in result.get("release-list", []):
            mbid = str(item.get("id", ""))
            if not mbid or mbid in seen:
                continue
            seen.add(mbid)
            candidates.append(_to_candidate(item))

    return candidates
