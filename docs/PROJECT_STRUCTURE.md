# PROJECT STRUCTURE

## Root Layout

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

Notes:
- 設定ファイル (config.yaml) は各コンポーネント内に配置
- 環境変数 (.env) は各コンポーネント内で管理し、Git には含めない

---

## Worker Structure

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

---

## Naming Rules

- snake_case for files
- PascalCase for classes
- verbs for functions (e.g., "fetch_metadata")

---

## Forbidden

- Mixing album-level and track-level logic
- Hardcoding paths or API keys