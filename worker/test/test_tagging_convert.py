"""convert_lossless_to_aiff のテスト。"""
from pathlib import Path

import pytest

from tagging.convert import (
    convert_flac_to_aiff,
    convert_lossless_to_aiff,
)


def _mock_probe(monkeypatch, sample_rate=44100, bits=16):
    """ffprobe のモックを設定する。"""
    monkeypatch.setattr(
        "tagging.convert._probe_audio",
        lambda _: {"sample_rate": str(sample_rate), "bits_per_raw_sample": str(bits)},
    )


def test_convert_lossless_to_aiff_converts_flac(monkeypatch, tmp_path: Path):
    src = tmp_path / "track.flac"
    src.write_bytes(b"x")

    called = {}
    _mock_probe(monkeypatch)

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
    _mock_probe(monkeypatch, sample_rate=44100, bits=16)

    def fake_run(cmd, check, capture_output, text):
        called["cmd"] = cmd

    monkeypatch.setattr("tagging.convert.subprocess.run", fake_run)

    out = convert_lossless_to_aiff(str(src))
    assert out.endswith("track.aiff")
    # ビット深度16 → pcm_s16be
    assert "-c:a" in called["cmd"]
    codec_idx = called["cmd"].index("-c:a")
    assert called["cmd"][codec_idx + 1] == "pcm_s16be"


def test_convert_lossless_to_aiff_downsample_when_exceeds_max(monkeypatch, tmp_path: Path):
    """96kHz/32bit のソースを max 48000/24 に制限する。"""
    src = tmp_path / "track.flac"
    src.write_bytes(b"x")

    called = {}
    _mock_probe(monkeypatch, sample_rate=96000, bits=32)

    def fake_run(cmd, check, capture_output, text):
        called["cmd"] = cmd

    monkeypatch.setattr("tagging.convert.subprocess.run", fake_run)

    out = convert_lossless_to_aiff(str(src), max_sample_rate=48000, max_bit_depth=24)
    assert out.endswith("track.aiff")
    # サンプルレート指定あり
    assert "-ar" in called["cmd"]
    ar_idx = called["cmd"].index("-ar")
    assert called["cmd"][ar_idx + 1] == "48000"
    # ビット深度 24 → pcm_s24be
    codec_idx = called["cmd"].index("-c:a")
    assert called["cmd"][codec_idx + 1] == "pcm_s24be"


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

    _mock_probe(monkeypatch)

    def fake_run(cmd, check, capture_output, text):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("tagging.convert.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="ffmpeg command not found"):
        convert_lossless_to_aiff(str(src))


def test_convert_flac_to_aiff_backward_compatible(monkeypatch, tmp_path: Path):
    src = tmp_path / "track.wav"
    src.write_bytes(b"x")

    _mock_probe(monkeypatch)

    def fake_run(cmd, check, capture_output, text):
        return None

    monkeypatch.setattr("tagging.convert.subprocess.run", fake_run)

    out = convert_flac_to_aiff(str(src))
    assert out.endswith("track.aiff")
