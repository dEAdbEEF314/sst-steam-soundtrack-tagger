from models import AlbumCandidate
from pipeline.flow import choose_best_candidate_for_title, refine_candidates_with_fallback_title


def test_choose_best_candidate_for_title_prefers_similarity_plus_score():
    candidates = [
        AlbumCandidate(mbid="a", title="Galactic Rest Stop", artist="Artist A", score=1.2),
        AlbumCandidate(mbid="b", title="Neon Skyline", artist="Artist B", score=2.0),
    ]

    chosen = choose_best_candidate_for_title(candidates, "Galactic Rest Stop")

    assert chosen is not None
    assert chosen.mbid == "a"


def test_choose_best_candidate_for_title_returns_none_for_empty():
    assert choose_best_candidate_for_title([], "anything") is None


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
