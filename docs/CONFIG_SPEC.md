# CONFIG SPEC

## acoustid

acoustid:
  api_key: ENV
  score_threshold: 0.9
  partial_verify_tracks: 3
  partial_match_threshold: 0.8

---

## search

search:
  languages:
    - ja
    - en
    - original
  strategy: merge

---

## album_match

album_match:
  track_count_tolerance: 1
  date_tolerance_days: 30

---

## retry

retry:
  max_attempts: 3
  base_delay_sec: 5

---

## format

format:
  lossless_target: aiff
  sample_rate: 48000
  bit_depth: 24

---

## paths

paths:
  input: /mnt/work_area
  review: s3://bucket/review/

---

## mode

mode:
  dry_run: false