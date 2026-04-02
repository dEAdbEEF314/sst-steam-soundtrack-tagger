# ERROR HANDLING

## General Rules

- All errors must be logged
- No silent failures
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

- Retry once
- If fail → move to review

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