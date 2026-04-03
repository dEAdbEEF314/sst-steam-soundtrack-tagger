# PREFECT FLOW

## Flow Name

sst-worker-pipeline

---

## Purpose

Steam soundtrack filesを入力し、候補検索・検証・タグ書き込み・保存までを
Prefectで可観測かつ再実行可能な形で実行する。

---

## Flow Parameters

- app_id: int
- files: list[str]
- config_path: str
- dry_run: bool = false

Notes:
- 入力契約は files を正とする。
- app_id が取得不能な場合でも files があれば実行可能にするが、精度低下をログで明示する。

---

## Task Graph

1. fetch_steam_metadata
2. search_musicbrainz_task
3. score_candidates_task
4. partial_acoustid_verify
5. full_acoustid_fallback
6. write_tags_task
7. persist_results

---

## Task Responsibilities

### fetch_steam_metadata
- Input: app_id
- Output: title variants, release_date
- Retry: config.retry.acoustid_max_attempts (default 3), exponential backoff
- デフォルトのタスクデコレータ: retries=2, retry_delay_seconds=5
- Flow 実行時に with_options で config の値に上書き

### search_musicbrainz_task
- Input: title variants
- Behavior: ja/en/original を統合検索して MBID 重複排除
- Output: candidate list
- Retry: config.retry.musicbrainz_max_attempts (default 2), exponential backoff

### score_candidates_task
- Input: candidates, local context
- Output: scored candidates, best candidate
- Note: もし明確なトップ候補かつスコアが非常に高い (>= cfg.acoustid.skip_acoustid_threshold) 場合は、以降のAcoustIDタスクを全てスキップしてタグ付け（Fast-track）へ移行する。

### partial_acoustid_verify
- Input: first N tracks, best candidate title, partial_tracks, threshold
- Output: match_ratio
- Rule: failure must escalate to full_acoustid_fallback

### full_acoustid_fallback
- Input: all tracks
- Output: resolved album or failure reason
- Note: fallback title is used to re-query and refine MusicBrainz candidates before final album/artist selection.

### write_tags_task
- Input: resolved metadata, files
- Output: tagging result summary

### persist_results
- Input: run artifacts
- Output: objects in SeaweedFS
- Paths:
	- ingest/ for source file reference manifests
	- archive/ for successful outputs
	- review/ for ambiguous or failed cases
	- workspace/ for run metadata and temporary/cache-like artifacts

---

## State and Transition Rules

- Preferred path:
	INGESTED -> IDENTIFIED -> FINGERPRINTED -> ENRICHED -> TAGGED -> STORED
- Fast-track path:
	INGESTED -> IDENTIFIED -> ENRICHED (AcoustID Skip, score >= skip_acoustid_threshold) -> TAGGED -> STORED
- Failure path:
	Any state -> FAILED -> review/

---

## Retry and Error Policy

- Config keys:
	- retry.max_attempts
	- retry.base_delay_sec
	- retry.backoff_strategy (default: exponential)
	- retry.base_backoff_factor (default: 2)
	- retry.acoustid_max_attempts (default: 3)
	- retry.musicbrainz_max_attempts (default: 2)
- Retry対象:
	- network timeouts
	- transient API failures
- Retry後も失敗:
	- fallback 可能なら fallback
	- 不可なら review/ へ送る
- Exponential Backoff:
	- retry_delay_seconds は [base_delay_sec * factor^0, base_delay_sec * factor^1, ...] のリストを生成
	- Prefect の with_options で適用

---

## Concurrency Policy (MVP)

- Album単位では逐次実行（まずは再現性優先）
- Track単位の並列化は将来拡張
- Deployment concurrency_limit は 1 から開始し、安定後に引き上げ

---

## Deployment Notes (MVP)

- Use Docker or Process work pool for self-hosted Prefect.
- Required runtime env:
	- PREFECT_API_URL
	- S3_ENDPOINT_URL
	- S3_ACCESS_KEY
	- S3_SECRET_KEY
	- S3_BUCKET
	- ACOUSTID_API_KEY
- Observe run states in Prefect UI and verify final artifacts in SeaweedFS.

Core operational scripts:
- core/prefect/setup-work-pool.ps1
- core/prefect/deploy-worker-flow.ps1
- core/prefect/run-worker-deployment.ps1

---

## Run Checklist

1. Prefect API reachable from worker.
2. SeaweedFS credentials valid (list/put/get success).
3. Trigger flow with app_id and files.
4. Confirm fallback behavior on partial verify failure.
5. Confirm archive/review outputs.

---

# END