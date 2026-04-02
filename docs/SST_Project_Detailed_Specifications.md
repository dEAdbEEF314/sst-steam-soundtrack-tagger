# SST Project - Detailed Specifications

## Overview

SST (Steam Soundtrack Tagger) is a distributed system designed to automatically identify and tag soundtracks purchased from Steam.

The system combines:

- Steam metadata
- MusicBrainz metadata
- AcoustID fingerprinting

to achieve near-fully automated tagging with minimal manual intervention.

---

## Scope

This system ONLY targets:

> Steam-purchased soundtracks

Assumptions:

- Audio files originate from Steam soundtrack depots
- Metadata may be incomplete or inconsistent
- Track filenames may not be reliable

---

## Identification Strategy

### Identification Strategy (Multi-layer Resolution)

SST uses a tiered resolution strategy to ensure metadata accuracy while minimizing site load:

1. **[Tier 1] Steam Store API**: Fetch basic info (Title, Release Date) using AppID.
2. **[Tier 2] MusicBrainz API**: Identify MBID, **DiscID**, and external VGMdb links.
3. **[Tier 3] VGMdb CDDB Emulator**: If DiscID is found, query VGMdb's freedb server (`ja.utf8`).
4. **[Tier 4] Targeted Parser**: If URL is found but no CDDB, use a polite parser (e.g., `beets-vgmdb` logic).
5. **[Tier 5] Fallback Search**: If no link is found, use Search API (Google/Bing) or controlled browser-use to identify URL.
6. **[Fallback] Review Queue**: Ambiguous cases are handled manually.

---

## Data Source Hierarchy (Priority)

In case of metadata mismatch between sources, the following priority applies:

1. **Manual Verification**: User-overridden values.
2. **MusicBrainz**: The primary "Source of Truth" for music-specific metadata.
3. **VGMdb**: Reliable for game-specific soundtrack details (Composers, Catalog Number).
4. **Steam Store**: Primary source for Title and AppID context (Release dates often differ from CD release).

---

## Phase 1: Steam Metadata-based Candidate Narrowing

### Input

- Steam AppID
- Local soundtrack title (localized)
- Steam release date
- Local track count

---

### Language Strategy

Search is performed using multiple language variants:

```yaml
search:
  languages:
    - ja
    - en
    - original
  strategy: merge
```

---

### Process

1. Fetch Steam metadata:
   - title
   - release_date

2. Generate queries:
   - Japanese title (primary)
   - English title
   - Original title (optional)

3. Query MusicBrainz (release search)

4. Merge results:
   - Deduplicate by MBID

---

### Filtering Conditions

Candidates must satisfy:

- format = Digital Media
- track count matches (± tolerance)
- release date matches (± tolerance)

---

### Scoring

```
score =
  title_similarity
  + track_count_match
  + release_date_match
  + format_match
```

---

### Selection

- If confidence >= threshold → ACCEPT
- Else → proceed to AcoustID verification

---

## Album Match Constraints

```yaml
album_match:
  track_count_tolerance: 1
  date_tolerance_days: 30
```

---

## Acoustic Fingerprinting

AcoustID is used for verification and fallback.

---

## Partial Verification

To reduce API usage:

- Only first N tracks are fingerprinted

```yaml
acoustid:
  partial_verify_tracks: 3
  partial_match_threshold: 0.8
```

---

### Decision Rule

- Match ratio >= threshold → ACCEPT
- Else → Full scan

---

## Full AcoustID Matching

Used when:

- No valid candidates
- Low confidence
- Partial verification fails

---

## Failure Handling

The system must handle the following failure scenarios:

- MusicBrainz returns no candidates:
  → Fallback to full AcoustID matching

- Fingerprint generation fails:
  → Retry according to retry policy

- Partial AcoustID verification fails:
  → Escalate to full fingerprint scan

- Full AcoustID matching fails:
  → Mark as FAILED and send to review queue

---

## State Management

Each track/album progresses through defined states:

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

## Track vs Album Separation

### Track Level

- fingerprint
- duration
- acoustid result

### Album Level

- track list consistency
- metadata
- artwork

---

## Cache Strategy

```yaml
cache:
  reuse_confidence_threshold: 0.95
  prefer_manual_verified: true
```

Rules:

- Successful results must be cached
- High-confidence matches are reusable
- Manual verification overrides all

---

## Logging

Each processing step must log:

```yaml
log:
  job_id:
  track_id:
  step:
  result:
  error:
```

---

## Review System

Failed or ambiguous cases are sent to:

```
s3://sst/review/
```

Each review item includes:

- YAML metadata
- Markdown comparison (diff)

---

## Dry Run Mode

```yaml
mode:
  dry_run: true
```

Behavior:

- No tag writing
- Full pipeline execution

---

## Output

### Album Output

```json
{
  "mbid": "...",
  "title": "...",
  "artist": "...",
  "confidence": 0.97
}
```

---

### Track Output

```json
{
  "title": "...",
  "track_number": 1,
  "duration": 123,
  "acoustid_score": 0.98
}
```

---

## Design Philosophy

SST is not a simple tagging tool.

It is:

> A distributed metadata inference system

Goals:

- Minimize manual review (<5%)
- Maximize reproducibility
- Enable future OSS database growth