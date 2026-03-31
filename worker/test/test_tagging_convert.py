from pathlib import Path

import pytest

from tagging.convert import (
    convert_flac_to_aiff,
    convert_lossless_to_aiff,
)


def test_convert_lossless_to_aiff_converts_flac(monkeypatch, tmp_path: Path):
    src = tmp_path / "track.flac"
    src.write_bytes(b"x")

    called = {}

    def fake_run(cmd, check, capture_output, text):
        called["cmd"] = cmd

    monkeypatch.setattr("tagging.convert.subprocess.run", fake_run)

    out = convert_lossless_to_aiff(str(src))
    assert out.endswith("track.aiff")
    assert called["cmd"][0] == "ffmpeg"
    assert called["cmd"][-1].endswith("track.aiff")


def test_convert_lossless_to_aiff_converts_wav(monkeypatch, tmp_path: Path):
    src = tmp_path / "track.wav"
    src.write_bytes(b"x")

    called = {}

    def fake_run(cmd, check, capture_output, text):
        called["cmd"] = cmd

    monkeypatch.setattr("tagging.convert.subprocess.run", fake_run)

    out = convert_lossless_to_aiff(str(src))
    assert out.endswith("track.aiff")
    assert called["cmd"][-3:] == ["-c:a", "pcm_s16be", str(tmp_path / "track.aiff")]


def test_convert_lossless_to_aiff_noop_for_mp3(tmp_path: Path):
    src = tmp_path / "track.mp3"
    src.write_bytes(b"x")

    out = convert_lossless_to_aiff(str(src))
    assert out == str(src)


def test_convert_lossless_to_aiff_noop_for_aiff(tmp_path: Path):
    src = tmp_path / "track.aiff"
    src.write_bytes(b"x")

    out = convert_lossless_to_aiff(str(src))
    assert out == str(src)


def test_convert_lossless_to_aiff_raises_when_ffmpeg_missing(monkeypatch, tmp_path: Path):
    src = tmp_path / "track.flac"
    src.write_bytes(b"x")

    def fake_run(cmd, check, capture_output, text):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("tagging.convert.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="ffmpeg command not found"):
        convert_lossless_to_aiff(str(src))


def test_convert_flac_to_aiff_backward_compatible(monkeypatch, tmp_path: Path):
    src = tmp_path / "track.wav"
    src.write_bytes(b"x")

    def fake_run(cmd, check, capture_output, text):
        return None

    monkeypatch.setattr("tagging.convert.subprocess.run", fake_run)

    out = convert_flac_to_aiff(str(src))
    assert out.endswith("track.aiff")
