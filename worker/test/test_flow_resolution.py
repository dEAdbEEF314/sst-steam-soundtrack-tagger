"""select_best_candidate / refine テストケース。"""
from models import AlbumCandidate, ScoredCandidate
from pipeline.flow import (
    _to_scored_candidates,
    refine_candidates_with_fallback_title,
    select_best_candidate,
)


def test_select_best_candidate_prefers_highest_final_score():
    scored = [
        ScoredCandidate(
            candidate=AlbumCandidate(mbid="a", title="Galactic Rest Stop", artist="Artist A", score=1.2),
            final_score=2.2,  # score 1.2 + similarity 1.0
        ),
        ScoredCandidate(
            candidate=AlbumCandidate(mbid="b", title="Neon Skyline", artist="Artist B", score=2.0),
            final_score=2.05,  # score 2.0 + low similarity
        ),
    ]

    chosen = select_best_candidate(scored)

    assert chosen is not None
    assert chosen.mbid == "a"


def test_select_best_candidate_returns_none_for_empty():
    assert select_best_candidate([]) is None


def test_to_scored_candidates_uses_fallback_title():
    candidates = [
        AlbumCandidate(mbid="a", title="Galactic Rest Stop", artist="Artist A", score=1.0),
        AlbumCandidate(mbid="b", title="Something Else", artist="Artist B", score=1.5),
    ]
    scored = _to_scored_candidates(candidates, fallback_title="Galactic Rest Stop")

    # "a" のタイトル類似度は 1.0 → final_score = 1.0 + 1.0 = 2.0
    # "b" のタイトル類似度は低い → final_score ≒ 1.5 + 低値
    best = select_best_candidate(scored)
    assert best is not None
    assert best.mbid == "a"


def test_refine_candidates_with_fallback_title_adds_new_candidate(monkeypatch):
    existing = [
        AlbumCandidate(mbid="x", title="Old Candidate", artist="A", track_count=2, score=0.5),
    ]

    def fake_search_releases(titles, limit=7):
        return [
            AlbumCandidate(
                mbid="y",
                title="Galactic Rest Stop",
                artist="B",
                track_count=31,
                release_date="2024-01-10",
            )
        ]

    monkeypatch.setattr("pipeline.flow.search_releases", fake_search_releases)

    refined = refine_candidates_with_fallback_title(
        existing,
        fallback_title="Galactic Rest Stop",
        files=[f"track_{i}.mp3" for i in range(31)],
        steam_release_date="2024-01-15",
    )

    assert any(c.mbid == "y" for c in refined)


def test_refine_candidates_with_fallback_title_keeps_existing_on_search_error(monkeypatch):
    existing = [AlbumCandidate(mbid="x", title="Keep Me", artist="A", score=1.0)]

    def fake_search_releases(_titles, limit=7):
        raise RuntimeError("network")

    monkeypatch.setattr("pipeline.flow.search_releases", fake_search_releases)

    refined = refine_candidates_with_fallback_title(
        existing,
        fallback_title="Whatever",
        files=["a.mp3"],
        steam_release_date=None,
    )

    assert refined == existing
