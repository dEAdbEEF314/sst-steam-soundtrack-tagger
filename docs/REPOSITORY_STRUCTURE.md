# REPOSITORY STRUCTURE

This document follows `PROJECT_STRUCTURE.md` as the source of truth.

sst/
 ├─ core/                # Prefect server / orchestration
 ├─ worker/              # Audio processing
 ├─ scout/               # Metadata discovery (optional)
 ├─ config/              # YAML configs
 ├─ docs/                # Documentation
 ├─ examples/            # Reference implementations
 └─ scripts/             # Utility scripts

---

worker/
 ├─ acoustid/            # AcoustID integration
 ├─ fingerprint/         # fpcalc wrapper
 ├─ musicbrainz/         # MB API client
 ├─ scoring/             # Candidate scoring logic
 ├─ tagging/             # ID3 writing
 ├─ pipeline/            # Orchestration logic
 └─ models/              # Data models

---

config/
 ├─ config.yaml
 ├─ core.yaml
 └─ worker.yaml