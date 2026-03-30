import json
import subprocess


def generate_fingerprint(audio_path: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["fpcalc", "-json", audio_path],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    return int(payload["duration"]), str(payload["fingerprint"])
