"""
Minimal SST Pipeline (Standalone)

- 単一音源ファイルをAcoustIDで照合
- 結果をprintするだけの最小構成
- Workerコンテナ内で実行する前提

Usage:
    docker exec -it sst-worker python examples/minimal_pipeline.py /mnt/work_area/test.flac
"""

import os
import sys
import json
import subprocess
import requests

ACOUSTID_API_URL = "https://api.acoustid.org/v2/lookup"


def run_fpcalc(file_path: str):
    """
    fpcalcを実行してfingerprintとdurationを取得
    """
    try:
        result = subprocess.run(
            ["fpcalc", "-json", file_path],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        return data["fingerprint"], data["duration"]
    except Exception as e:
        raise RuntimeError(f"fpcalc failed: {e}")


def query_acoustid(fingerprint: str, duration: int, api_key: str):
    """
    AcoustID APIへ問い合わせ
    """
    params = {
        "client": api_key,
        "meta": "recordings releases releasegroups",
        "duration": duration,
        "fingerprint": fingerprint,
    }

    response = requests.get(ACOUSTID_API_URL, params=params, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"AcoustID API error: {response.status_code}")

    return response.json()


def parse_best_match(result_json: dict):
    """
    最もスコアの高い結果を抽出
    """
    results = result_json.get("results", [])
    if not results:
        return None

    best = max(results, key=lambda x: x.get("score", 0))

    recordings = best.get("recordings", [])
    if not recordings:
        return {
            "score": best.get("score"),
            "title": None,
            "artist": None,
        }

    rec = recordings[0]

    title = rec.get("title")
    artists = rec.get("artists", [])
    artist_name = artists[0]["name"] if artists else None

    return {
        "score": best.get("score"),
        "title": title,
        "artist": artist_name,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python minimal_pipeline.py <audio_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    api_key = os.getenv("ACOUSTID_API_KEY")
    if not api_key:
        print("ERROR: ACOUSTID_API_KEY is not set")
        sys.exit(1)

    print("=== SST Minimal Pipeline ===")
    print(f"File: {file_path}")

    # Step 1: fingerprint
    print("\n[1] Running fpcalc...")
    fingerprint, duration = run_fpcalc(file_path)
    print(f"Duration: {duration}s")

    # Step 2: AcoustID query
    print("\n[2] Querying AcoustID...")
    result_json = query_acoustid(fingerprint, duration, api_key)

    # Step 3: parse result
    print("\n[3] Parsing result...")
    best = parse_best_match(result_json)

    print("\n=== RESULT ===")
    if best:
        print(f"Score : {best['score']}")
        print(f"Title : {best['title']}")
        print(f"Artist: {best['artist']}")
    else:
        print("No match found")


if __name__ == "__main__":
    main()