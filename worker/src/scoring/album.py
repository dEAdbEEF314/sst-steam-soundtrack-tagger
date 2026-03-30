from datetime import datetime

from models import AlbumCandidate


def _date_score(candidate_date: str | None, steam_date: str | None, tolerance_days: int) -> float:
    if not candidate_date or not steam_date:
        return 0.0
    try:
        c = datetime.fromisoformat(candidate_date[:10])
        s = datetime.fromisoformat(steam_date[:10])
    except ValueError:
        return 0.0
    return 1.0 if abs((c - s).days) <= tolerance_days else 0.0


def score_candidates(
    candidates: list[AlbumCandidate],
    local_track_count: int,
    steam_release_date: str | None,
    tolerance_days: int = 30,
) -> list[AlbumCandidate]:
    for c in candidates:
        track_score = 1.0 if c.track_count is not None and abs(c.track_count - local_track_count) <= 1 else 0.0
        c.score = track_score + _date_score(c.release_date, steam_release_date, tolerance_days)
    return sorted(candidates, key=lambda x: x.score, reverse=True)
