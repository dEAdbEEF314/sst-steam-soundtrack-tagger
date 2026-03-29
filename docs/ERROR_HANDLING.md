# ERROR HANDLING

## General Rules

- All errors must be logged
- No silent failures
- Retry must be controlled via config

---

## Cases

### AcoustID Timeout

- Retry: 3 times
- Backoff: exponential

---

### MusicBrainz Failure

- Retry: 2 times
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

- Always retry with backoff

---

## Logging Format

- job_id
- track_id
- step
- error