ATA FLOW

## Overview

SST processes Steam-purchased soundtrack files through a multi-phase identification pipeline.

---

## Pipeline

1. INPUT

- Source: Local audio files (/mnt/work_area)
- Metadata: Steam AppID (optional but recommended)

---

2. STEAM METADATA FETCH

- Input: AppID
- Output:
  - title (localized)
    - release_date

---

3. MUSICBRAINZ SEARCH (MULTI-LANGUAGE MERGE)

- Input:
  - title (ja → en → original)
- Process:
  - Perform multiple queries
  - Merge results
  - Deduplicate by MBID

- Output:
  - candidate albums

---

4. CANDIDATE FILTERING

Conditions:
- format = Digital Media
- track_count ≈ local file count (±1)
- release_date ≈ Steam release date (±30 days)

---

5. SCORING

Each candidate receives a score:

score =
  title_similarity +
  track_count_match +
  release_date_match +
  format_match

---

6. DECISION

- If score ≥ threshold:
  → proceed to partial verification
- Else:
  → fallback to full AcoustID

---

7. PARTIAL ACOUSTID VERIFICATION

- Input: first 3 tracks
- Process:
  - fingerprint
  - match via AcoustID

- If match_ratio ≥ 0.8:
  → ACCEPT album
- Else:
  → fallback to full AcoustID

---

8. FULL ACOUSTID (FALLBACK)

- Process all tracks
- Aggregate matches
- Determine album

---

9. TAGGING

- Write ID3v2.3 tags
- Normalize metadata

---

10. STORAGE

- Save processed files
- Store metadata JSON
- Upload review cases to MinIO

---

## Notes

- Album-level and track-level logic MUST be separated
- All decisions must be deterministic and reproducible
