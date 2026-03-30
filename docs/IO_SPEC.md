# IO Specification

---

## Input

```json
{
  "app_id": 123456,
  "files": [
    "/mnt/work_area/album/01.flac"
  ]
}
```

---

## Output

```json
{
  "status": "SUCCESS",
  "album": "...",
  "confidence": 0.95
}
```

---

## Internal

```json
{
  "state": "PROCESSING",
  "node": "worker"
}
```

---

# END
