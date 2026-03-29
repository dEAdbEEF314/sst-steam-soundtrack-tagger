ST Input / Output Specification

## Input

```json
{
      "app_id": 123456,
        "input_dir": "./audio/",
          "files": [
              "track01.flac",
                  "track02.flac"
                    ]
}
```

---

## Intermediate (Album Candidate)

```json
{
      "candidates": [
          {
                    "mbid": "xxx",
                          "title": "Album Name",
                                "track_count": 12,
                                      "release_date": "2023-05-01",
                                            "score": 2.8
                                                }
                                                  ]
}
```

---

## Output

```json
{
      "album": {
              "title": "Example Album",
                  "artist": "Composer",
                      "release_date": "2023-05-01"
                        },
                          "tracks": [
                              {
                                        "track_number": 1,
                                              "title": "Track 01"
                                                  }
                                                    ],
                                                      "confidence": 0.92,
                                                        "status": "SUCCESS"
}
```

---

## Failure Output

```json
{
      "status": "REVIEW_REQUIRED",
        "reason": "low_confidence"
}
```

