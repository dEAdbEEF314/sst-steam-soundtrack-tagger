from pipeline.flow import full_acoustid_fallback


def test_full_fallback_returns_no_files_reason():
    result = full_acoustid_fallback.fn([], api_key="test", api_url="http://test")
    assert result["resolved"] is False
    assert result["reason"] == "no_files"


def test_full_fallback_match_ratio_present_when_resolved(monkeypatch):
    monkeypatch.setattr("pipeline.flow.generate_fingerprint", lambda _f: (120, "fp"))
    monkeypatch.setattr(
        "pipeline.flow.identify_track",
        lambda _d, _fp, api_key, api_url: {"recordings": [{"title": "Track X"}]},
    )

    result = full_acoustid_fallback.fn(["a.mp3", "b.mp3"], api_key="test", api_url="http://test")

    assert result["resolved"] is True
    assert result["matched_tracks"] == 2
    assert result["match_ratio"] == 1.0
