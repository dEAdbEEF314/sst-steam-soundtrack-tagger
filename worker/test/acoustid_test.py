import pytest

from acoustid_api.client import extract_recording_title, identify_track


def test_extract_recording_title_handles_missing_data():
    assert extract_recording_title(None) is None
    assert extract_recording_title({}) is None
    assert extract_recording_title({"recordings": [{"title": "Track A"}]}) == "Track A"


def test_identify_track_requires_api_key(monkeypatch):
    monkeypatch.delenv("ACOUSTID_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        identify_track(duration=120, fingerprint="dummy")
