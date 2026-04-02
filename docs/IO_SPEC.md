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
  "app_id": 123456,
  "file_refs": ["/mnt/work_area/album/01.flac"],
  "status": "success",
  "resolved": {
    "resolved": true,
    "album": "Example Album",
    "artist": "Example Artist",
    "mbid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "resolution": "partial",
    "partial_ratio": 0.85
  },
  "tag_result": {
    "updated": 1,
    "dry_run": false
  },
  "candidate_count": 5,
  "storage": {
    "bucket": "sst",
    "key": "archive/app_123456_20260101T000000Z.json"
  }
}
```

status values: "success" | "review"

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
