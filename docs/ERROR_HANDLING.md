# ERROR HANDLING

## General Rules

- All errors must be logged
- No silent failures
  - 非対応フォーマット（MP3 以外）のファイルを `write_tags` がスキップする場合も WARNING レベルでログ出力を行うこと
- Retry must be controlled via config

---

## Cases

### AcoustID Timeout

- Retry: 3 times (configurable via retry.acoustid_max_attempts)
- Backoff: exponential (base_delay_sec * base_backoff_factor^n)
- Backoff 戦略と係数は config で変更可能

---

### MusicBrainz Failure

- Retry: 2 times (configurable via retry.musicbrainz_max_attempts)
- Backoff: exponential
- If still failing → fallback to AcoustID

---

### Fingerprint Failure

- Mark track as FAILED
- Skip album if >50% fail

---

### Tag Write Failure

- Supported formats: MP3 (ID3v2.3) — FLAC / WAV / AIFF 対応は Phase 3 追加実装タスク参照
- Non-MP3 files: `write_tags` は WARNING をログ出力してスキップする（サイレント無視禁止）
- Retry once
- If fail → move to review
- `write_tags_task` には `retries=1` を付与すること（現実装では未設定 — Phase 3 修正タスク参照）

---

### Network Errors

- Always retry with exponential backoff

---

## Config Keys

- retry.max_attempts: デフォルトのリトライ回数
- retry.base_delay_sec: ベース遅延秒数
- retry.backoff_strategy: バックオフ戦略 (exponential)
- retry.base_backoff_factor: バックオフ係数 (default: 2)
- retry.acoustid_max_attempts: AcoustID 専用リトライ回数
- retry.musicbrainz_max_attempts: MusicBrainz 専用リトライ回数

---

## Implementation Notes

- Prefect タスクデコレータでデフォルトのリトライ値を設定
- Flow 内で with_options を使って config の値に上書き
- retry_delay_seconds にはリスト形式で指数バックオフ列を渡す

---

## Logging Format

- job_id
- track_id
- step
- error