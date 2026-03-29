# SST Project – Recruitment, Systems and Tools (Final Complete)

## Overview

This document defines the infrastructure, execution model, and required tools
for the SST (Steam Soundtrack Tagger) system.

SST is a distributed, containerized, Prefect-orchestrated pipeline designed to:
- Process Steam soundtrack files
- Identify tracks using acoustic fingerprinting
- Enrich metadata using MusicBrainz and AcoustID
- Enable human-assisted correction when needed

---

## Execution Model

All code is developed locally but executed inside Docker containers.

- Development: VS Code (local machine)
- Source of truth: GitHub repository
- Execution: Docker containers (Worker / Core / Scout)
- Deployment: git pull + docker compose up -d --build

Critical rules:

- No code runs directly on host OS
- All execution must be reproducible via Docker
- Config changes must NOT require image rebuilds
- Behavior must be controlled via config.yaml

---

## System Architecture

### Components

| Component        | Role |
|-----------------|------|
| SST-Core-VM     | Prefect Server / orchestration |
| SST-Worker-CT   | Audio processing / tagging |
| SST-Scout-VM    | Steam metadata ingestion |
| MinIO           | Object storage / cache / artifacts |

---

### High-Level Flow

1. Scout fetches Steam metadata
2. Core schedules jobs via Prefect
3. Worker processes audio:
   - Fingerprinting (fpcalc / AcoustID)
   - MusicBrainz lookup
   - Metadata merging
   - Tag writing
4. Results:
   - Stored in MinIO
   - OR sent to review queue

---

## Container Design

### Worker Container

Responsibilities:

- Audio decoding (ffmpeg)
- Fingerprinting (fpcalc / chromaprint)
- AcoustID API calls
- MusicBrainz queries
- Metadata normalization
- Tag writing (mutagen)

Mount path:

/mnt/work_area

Characteristics:

- Stateless (except local cache)
- Horizontally scalable
- Safe to terminate anytime

---

### Core Container

Responsibilities:

- Prefect Server
- Flow orchestration
- Job scheduling
- State tracking

Exposes:

http://<core-host>:4200

API:

/api

---

### Scout Container

Responsibilities:

- Steam API access
- Metadata extraction:
  - AppID
  - Title
  - Release date
- Preprocessing for album matching

---

### MinIO (Object Storage)

Responsibilities:

- Store processed outputs
- Store logs and artifacts
- Store cache data
- Store review queue data

Example structure:

bucket:
  ├─ processed/
  ├─ cache/
  ├─ logs/
  └─ review/

---

## Directory Layout (Repository)

SST_Project/
├─ worker/
│  ├─ Dockerfile
│  ├─ docker-compose.yml
│  ├─ docker-compose.dev.yml
│  ├─ config.yaml
│  ├─ .env
│  └─ src/
│
├─ core/
│  ├─ docker-compose.yml
│  └─ .env
│
├─ scout/
│  ├─ Dockerfile
│  └─ docker-compose.yml
│
├─ docs/
│  ├─ SST_Project_Detailed_Specifications.md
│  └─ SST_Project_Recruitment_Systems_and_Tools.md
│
└─ examples/
   └─ minimal_pipeline.py

---

## Environment Configuration

### .env (Secrets ONLY)

ACOUSTID_API_KEY=xxx
MINIO_ACCESS_KEY=xxx
MINIO_SECRET_KEY=xxx
PREFECT_API_URL=http://sst-core-vm:4200/api

Rules:

- Never commit .env
- Inject via Docker or environment

---

### config.yaml (Behavior control)

acoustid:
  score_threshold: 0.9
  score_gap: 0.05
  partial_verify_tracks: 3
  partial_match_threshold: 0.8

search:
  languages:
    - ja
    - en
    - original
  strategy: merge

album_match:
  track_count_tolerance: 1
  date_tolerance_days: 30

retry:
  max_attempts: 3
  backoff_seconds: 5

---

## Docker Strategy

### Principles

- Config changes must NOT trigger rebuild
- Use bind mounts for:
  - config.yaml
  - work_area
- Separate dev/prod compose files

---

### Dev

docker-compose.dev.yml

- Fast iteration
- Local volume mounts
- Debug logging enabled

---

### Production

docker-compose.yml

- Stable execution
- Minimal logging
- Restart policies enabled

---

## Networking

### Internal

- Worker → Core (Prefect API)
- Worker → MinIO
- Scout → Steam API

---

### Core Endpoint

http://sst-core-vm.outergods.lan:4200/api

Health:

/api/health

---

## Required Tools

### Core Stack

- Python 3.11+
- Docker / Docker Compose
- Prefect 2.x
- ffmpeg
- chromaprint (fpcalc)

---

### Python Libraries

- prefect
- httpx
- pydantic
- mutagen
- pyacoustid
- musicbrainzngs

---

### Development Tools

- VS Code
- GitHub Copilot
- AI coding agents (optional)

---

## Fingerprinting Requirements

fpcalc must exist inside container.

Check:

fpcalc -version

---

## Failure Handling

Must handle:

- MusicBrainz returns 0 → fallback to AcoustID
- Fingerprint fails → retry
- Low confidence → full scan
- API timeout → retry with backoff
- Final failure → send to review queue

---

## Caching Strategy

- Cache successful matches
- Reuse if confidence > 0.95
- Cache stored in MinIO
- Manual corrections override cache

---

## Review System

Stored in MinIO:

review/
 ├─ job_id/
 │   ├─ metadata.yaml
 │   └─ diff.md

Contains:

- Candidate comparisons
- Editable corrections

---

## Logging

Each job must log:

- job_id
- track_id
- processing step
- result
- error

Logs must be:

- Structured (JSON preferred)
- Stored in MinIO

---

## Scaling Strategy

- Workers are horizontally scalable
- Prefect distributes jobs
- No shared state dependency

---

## AI Agent Compatibility

This project is explicitly designed for AI-assisted development.

Guarantees:

- No hidden assumptions
- All configs externalized
- Deterministic execution paths
- Clear separation of roles

AI agents must be able to:

- Implement features without guessing environment
- Run flows without manual intervention
- Extend pipeline safely

---

## Development Workflow

1. Edit locally (VS Code)
2. Commit to GitHub
3. Pull on server
4. docker compose up -d --build

---

## Future Extensions

- Web-based review UI
- Shared metadata database
- Distributed worker auto-scaling
- OSS contribution model

---

## Summary

SST is a distributed audio identification system combining:

- Acoustic fingerprinting (AcoustID)
- Metadata intelligence (MusicBrainz + Steam)
- Human-in-the-loop validation
- Container-based scalable execution

It is designed for both human developers and AI agents.

---