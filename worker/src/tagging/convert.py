"""ロスレスオーディオの AIFF 変換。

max_sample_rate / max_bit_depth を上限として使用する。
ソースがこれ以下の場合はそのまま維持し、超過時のみダウンサンプル/ビット深度削減を行う。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


LOSSLESS_EXTENSIONS: frozenset[str] = frozenset({".flac", ".wav", ".aif", ".aiff"})

# ビット深度に対応する AIFF PCM コーデック
_BIT_DEPTH_CODEC: dict[int, str] = {
    16: "pcm_s16be",
    24: "pcm_s24be",
    32: "pcm_s32be",
}


def _probe_audio(file_path: str) -> dict:
    """ffprobe でオーディオストリーム情報を取得する。"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "a:0",
        "-show_streams",
        "-of", "json",
        file_path,
    ]
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        data = json.loads(proc.stdout)
        streams = data.get("streams", [])
        return streams[0] if streams else {}
    except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError):
        return {}


def convert_lossless_to_aiff(
    file_path: str,
    max_sample_rate: int = 48000,
    max_bit_depth: int = 24,
) -> str:
    """ロスレスオーディオファイルを AIFF に変換する。

    - 既に AIFF の場合はそのまま返す
    - ロスレスでないファイルもそのまま返す
    - サンプルレート/ビット深度がmax以下ならソースのまま維持
    - 超過している場合のみダウンサンプル/ビット深度削減
    """
    src = Path(file_path)
    suffix = src.suffix.lower()

    if suffix in (".aiff", ".aif"):
        return str(src)

    if suffix not in LOSSLESS_EXTENSIONS:
        return str(src)

    # ソースのオーディオ情報を取得
    info = _probe_audio(file_path)
    src_sample_rate = int(info.get("sample_rate", 0)) or None
    # bits_per_raw_sample は ffprobe で取得できるフィールド
    src_bit_depth = int(info.get("bits_per_raw_sample", 0)) or None

    # 出力パラメータを決定 (ソース以下かつmax以下)
    out_sample_rate: int | None = None
    if src_sample_rate and src_sample_rate > max_sample_rate:
        out_sample_rate = max_sample_rate

    out_bit_depth = min(
        src_bit_depth if src_bit_depth else max_bit_depth,
        max_bit_depth,
    )
    codec = _BIT_DEPTH_CODEC.get(out_bit_depth, "pcm_s24be")

    dst = src.with_suffix(".aiff")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-c:a", codec,
    ]

    if out_sample_rate:
        cmd.extend(["-ar", str(out_sample_rate)])

    cmd.append(str(dst))

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg command not found") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"ffmpeg conversion failed: {stderr}") from exc

    return str(dst)


def convert_flac_to_aiff(file_path: str) -> str:
    """後方互換ラッパー。"""
    return convert_lossless_to_aiff(file_path)
