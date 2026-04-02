# REPOSITORY STRUCTURE

This document follows `PROJECT_STRUCTURE.md` as the source of truth.

SST_Project/
 ├─ core/                # Prefect server / orchestration
 │   ├─ docker-compose.yml
 │   └─ prefect/         # デプロイ・運用スクリプト
 ├─ worker/              # Audio processing
 │   ├─ Dockerfile
 │   ├─ docker-compose.yml
 │   ├─ docker-compose.dev.yml
 │   ├─ config.yaml
 │   ├─ requirements.txt
 │   └─ src/
 ├─ scout/               # Steam library scanning / metadata ingestion
 │   ├─ Dockerfile
 │   ├─ docker-compose.yml
 │   ├─ docker-compose.dev.yml
 │   ├─ config.yaml
 │   ├─ .env.example
 │   ├─ requirements.txt
 │   ├─ src/
 │   └─ test/
 ├─ docs/                # Documentation
 ├─ examples/            # Reference implementations
 └─ work_area/           # ランタイム作業ディレクトリ

---

worker/src/
 ├─ acoustid/            # AcoustID integration (pyacoustid)
 ├─ acoustid_api/        # AcoustID REST API client
 ├─ fingerprint/         # fpcalc wrapper
 ├─ musicbrainz/         # MB API client
 ├─ scoring/             # Candidate scoring logic
 ├─ steam/               # Steam Store API client
 ├─ tagging/             # ID3 writing / audio conversion
 ├─ pipeline/            # Prefect flow + orchestration logic
 └─ models/              # Data models (Pydantic)