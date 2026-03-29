# SST Copilot Instructions

## Project Overview

This project (SST: Steam Soundtrack Tagger) is a distributed system for automatically tagging Steam-purchased soundtrack files.

Core architecture:

- Prefect (workflow orchestration)
- Worker containers (audio processing)
- AcoustID (audio fingerprinting)
- MusicBrainz (metadata)
- MinIO (storage)
- Steam API (metadata source)

---

## Key Design Principles

1. Steam-purchased soundtracks only
2. Accuracy over speed
3. Multi-phase identification:
   - Phase 1: MusicBrainz album narrowing
   - Phase 2: Partial AcoustID verification
   - Phase 3: Full AcoustID fallback

---

## Coding Rules

- Language: Python 3.11+
- Use `uv` for dependency management
- Prefer async where possible
- All configs must come from config.yaml or env

---

## Worker Responsibilities

- Generate fingerprint using fpcalc
- Query AcoustID
- Perform partial verification (first 3 tracks)
- Return structured JSON result

---

## DO NOT

- Hardcode API keys
- Mix album-level and track-level logic
- Assume single-language titles

---

## Expected Output Style

- Clean, modular Python code
- Type hints required
- Logging included