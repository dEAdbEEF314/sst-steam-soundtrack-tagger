# PROJECT STRUCTURE

## Root Layout

sst/
 ├─ core/                # Prefect server / orchestration
 ├─ worker/              # Audio processing
 ├─ scout/               # Metadata discovery (optional)
 ├─ config/              # YAML configs
 ├─ docs/                # Documentation
 ├─ examples/            # Reference implementations
 └─ scripts/             # Utility scripts

---

## Worker Structure

worker/
 ├─ acoustid/            # AcoustID integration
 ├─ fingerprint/         # fpcalc wrapper
 ├─ musicbrainz/         # MB API client
 ├─ scoring/             # Candidate scoring logic
 ├─ tagging/             # ID3 writing
 ├─ pipeline/            # Orchestration logic
 └─ models/              # Data models

---

## Config

config/
 ├─ config.yaml
 ├─ core.yaml
 ├─ worker.yaml

---

## Naming Rules

- snake_case for files
- PascalCase for classes
- verbs for functions (e.g., "fetch_metadata")

---

## Forbidden

- Mixing album-level and track-level logic
- Hardcoding paths or API keys