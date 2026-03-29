# SST Task Breakdown

## Phase 1: Core Infrastructure

### 1. Steam API Client

* Fetch metadata using AppID
* Extract:

  * title
    * release_date

### 2. MusicBrainz Client

* Implement release search API
* Handle query building
* Handle pagination & rate limiting

---

## Phase 2: Search & Matching

### 3. Query Builder

* Multi-language query generation
* Boost handling (^3, ^2)
* Date range query

### 4. Candidate Fetcher

* Execute parallel queries
* Merge results
* Deduplicate by MBID

### 5. Candidate Filter

* Filter by:

  * format (Digital Media)
    * track count tolerance
      * date tolerance

### 6. Scoring Engine

* Implement:

  * title similarity
    * track count score
      * date score
        * format score
        * Return ranked candidates

        ---

## Phase 3: Verification

### 7. AcoustID Wrapper

* Generate fingerprint (fpcalc)
* Query AcoustID API
* Parse response

### 8. Partial Verification

* Select first N tracks
* Compute match ratio
* Decide accept/reject

### 9. Full Matching (Fallback)

* Fingerprint all tracks
* Aggregate results

---

## Phase 4: Metadata Processing

### 10. Metadata Builder

* Construct final album/track metadata

### 11. Tag Writer

* Write ID3v2.3 tags
* Support AIFF/FLAC/MP3

---

## Phase 5: System

### 12. Storage Handler

* Save to MinIO
* Organize folders

### 13. Review Generator

* Output YAML + Markdown diff

### 14. Cache System

* Store successful matches
* Reuse high-confidence entries

---

## Phase 6: Integration

### 15. Pipeline Orchestrator

* Connect all modules
* Manage state transitions

### 16. CLI Interface

* Input: AppID + directory
* Output: processed files

