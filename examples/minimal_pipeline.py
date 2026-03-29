"""
Minimal SST Pipeline (Prefect Flow)

This is the entrypoint for the SST system.
Runs inside worker container.

Usage:
    python minimal_pipeline.py --input /mnt/work_area/test.flac
"""

from prefect import flow, task
import os
import subprocess
import acoustid
import musicbrainzngs

ACOUSTID_API_KEY = os.getenv("ACOUSTID_API_KEY")


@task
def fingerprint(file_path: str):
    """Generate fingerprint using fpcalc"""
    try:
        result = subprocess.run(
            ["fpcalc", "-json", file_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except Exception as e:
        raise RuntimeError(f"Fingerprint failed: {e}")


@task
def identify_with_acoustid(file_path: str):
    """Identify track using AcoustID"""
    try:
        duration, fp = acoustid.fingerprint_file(file_path)
        results = acoustid.lookup(ACOUSTID_API_KEY, fp, duration)

        if "results" not in results or len(results["results"]) == 0:
            return None

        return results["results"][0]
    except Exception as e:
        raise RuntimeError(f"AcoustID failed: {e}")


@task
def search_musicbrainz(title: str):
    """Search release via MusicBrainz"""
    musicbrainzngs.set_useragent("sst", "0.1")

    try:
        result = musicbrainzngs.search_releases(
            release=title,
            limit=5
        )
        return result
    except Exception as e:
        raise RuntimeError(f"MusicBrainz search failed: {e}")


@task
def process_file(file_path: str):
    """Main processing logic for one file"""

    print(f"[INFO] Processing: {file_path}")

    # Step 1: Fingerprint
    fp = fingerprint(file_path)

    # Step 2: AcoustID
    acoustid_result = identify_with_acoustid(file_path)

    if not acoustid_result:
        print("[WARN] No AcoustID result")
        return

    # Extract title
    try:
        title = acoustid_result["recordings"][0]["title"]
    except Exception:
        print("[WARN] No title found")
        return

    print(f"[INFO] Detected title: {title}")

    # Step 3: MusicBrainz
    mb_result = search_musicbrainz(title)

    print("[INFO] MusicBrainz result:", mb_result)


@flow(name="sst-minimal-pipeline")
def sst_pipeline(input_path: str):
    """Prefect Flow entrypoint"""

    if os.path.isfile(input_path):
        process_file(input_path)
    else:
        for file in os.listdir(input_path):
            full_path = os.path.join(input_path, file)
            if full_path.endswith((".flac", ".mp3", ".wav")):
                process_file(full_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    sst_pipeline(args.input)