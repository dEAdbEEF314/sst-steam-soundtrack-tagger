# SST (Steam Soundtrack Tagger) - Detailed Specifications

---

## 1. Overview

SST is a metadata normalization pipeline designed specifically for **soundtracks purchased via Steam**.

It identifies, enriches, and tags audio files using a hybrid strategy combining:

* Steam metadata
* MusicBrainz search (multi-language merged strategy)
* AcoustID fingerprinting (partial verification + full fallback)

---

## 2. Scope

### Target

* Soundtracks purchased via Steam
* Audio files with missing or unreliable metadata

### Non-Target

* Streaming audio
* Non-Steam audio collections
* Live recordings or user-modified audio

---

## 3. High-Level Pipeline

```
[Input Audio Files]
        ↓
        [Steam Metadata Fetch (AppID)]
                ↓
                [MusicBrainz Album Candidate Search]
                        ↓
                        [Candidate Filtering & Scoring]
                                ↓
                                [Album Determination]
                                        ↓
                                        [Partial AcoustID Verification (3 tracks)]
                                                ↓
                                                [Full AcoustID Fallback (if needed)]
                                                        ↓
                                                        [Metadata Enrichment]
                                                                ↓
                                                                [Tag Writing]
                                                                        ↓
                                                                        [Storage (MinIO)]
                                                                                ↓
                                                                                [Review Queue (if necessary)]
                                                                                ```

                                                                                ---

## 4. Input Requirements

### Required

* Steam AppID
* Local audio files (same album)

### Derived

* Track count
* File duration
* AcoustID fingerprints

---

## 5. Steam Metadata Acquisition

### Source

* Steam Store API

### Required Fields

* Title (localized)
* Release date

### Notes

* Date precision may vary (year-only possible)
* Title may differ from MusicBrainz entries

---

## 6. MusicBrainz Search Strategy

### Endpoint

```
/ws/2/release/
```

---

### Multi-Language Strategy

Search is executed in parallel using multiple title variants and merged.

```yaml
search:
  languages:
      - ja
          - en
              - original
                strategy: merge
                ```

                ---

### Query Template

```
(
  release:"{title_ja}"^3 OR
    release:"{title_en}"^2 OR
      release:"{title_original}"
      )
AND format:digital
AND date:[{YYYY}-01-01 TO {YYYY}-12-31]
```

---

### Result Handling

* Merge results from all queries
* Deduplicate by MBID
* Limit to top N candidates (e.g., 20)

---

## 7. Candidate Filtering

```yaml
album_match:
  track_count_tolerance: 1
    date_tolerance_days: 30
    ```

### Conditions

* Format must be Digital Media
* Track count within tolerance
* Release date within tolerance

---

## 8. Candidate Scoring

```
score =
  title_similarity
    + track_count_score
      + release_date_score
        + format_score
        ```

        ---

### Title Similarity

* Normalize text (lowercase, remove symbols, normalize Unicode)
* Use string similarity (e.g., Levenshtein or token-based)

---

### Track Count Score

* Exact match → 1.0
* ±1 difference → 0.7
* Otherwise → 0

---

### Release Date Score

* Within 7 days → 1.0
* Within 30 days → 0.7
* Within 90 days → 0.4
* Otherwise → 0

---

### Format Score

* Digital Media → 1.0
* Otherwise → 0

---

### Acceptance Threshold

```yaml
search:
  accept_threshold: 2.5
  ```

  ---

## 9. Album Determination

* Select candidate with highest score
* If score ≥ threshold → ACCEPT
* Otherwise → fallback to AcoustID

---

## 10. Partial AcoustID Verification

### Configuration

```yaml
acoustid:
  partial_verify_tracks: 3
    partial_match_threshold: 0.8
    ```

    ---

### Process

1. Select first N tracks (default: 3)
2. Generate fingerprints
3. Query AcoustID
4. Compare results with selected album

---

### Acceptance

* Match ratio ≥ threshold → ACCEPT
* Otherwise → Full AcoustID

---

## 11. Full AcoustID Matching (Fallback)

### Trigger

* No confident album candidate
* Partial verification failed

### Process

* Fingerprint all tracks
* Match each track individually
* Reconstruct album from matches

---

## 12. Metadata Enrichment

### Sources

* MusicBrainz
* Cover Art Archive

### Fields

* Album title
* Track title
* Artist
* Track number
* Disc number
* Release date
* Artwork

---

## 13. Tag Writing

### Format

* ID3v2.3 (strict)

### Rules

* Overwrite existing metadata
* Preserve audio integrity

---

## 14. Storage

### Backend

* MinIO (S3-compatible)

### Structure

```
bucket/
  ├─ processed/
    ├─ review/
      └─ logs/
      ```

      ---

## 15. Review System

### Trigger Conditions

* Low confidence score
* Conflicting identification results

### Output

* YAML metadata
* Markdown diff comparison

---

## 16. Cache Strategy

* Cache all successful matches
* Reuse only if confidence ≥ 0.95
* manual_verified entries override all

---

## 17. State Management

```
INGESTED
FINGERPRINTED
IDENTIFIED
ENRICHED
TAGGED
STORED
FAILED
```

---

## 18. Logging

### Fields

* job_id
* track_id
* step
* result
* error

---

## 19. Config Structure

```yaml
search:
  languages: [ja, en, original]
    accept_threshold: 2.5

    album_match:
      track_count_tolerance: 1
        date_tolerance_days: 30

        acoustid:
          partial_verify_tracks: 3
            partial_match_threshold: 0.8
            ```

            ---

## 20. Design Principles

* Deterministic processing
* Minimize false positives
* Prefer precision over recall
* Human-in-the-loop fallback
* Cache-driven improvement

---

## 21. Key Insight

SST is not just a tagging tool.

It is a **metadata resolution system** that combines:

* Metadata inference
* Acoustic verification
* Human validation

---

# END

