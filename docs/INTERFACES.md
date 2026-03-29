# INTERFACES

## Data Types

### Track
- path: str
- duration: float

### AlbumCandidate
- mbid: str
- title: str
- track_count: int
- release_date: str

---

## Functions

### fingerprint

fingerprint(audio_path: str) -> str

- Returns Chromaprint fingerprint

---

### acoustid_match

acoustid_match(fingerprint: str) -> list[Match]

Match:
- score: float
- recording_id: str
- title: str
- artist: str

---

### search_musicbrainz

search_musicbrainz(title: str) -> list[AlbumCandidate]

---

### score_candidates

score_candidates(candidates: list[AlbumCandidate], context) -> list[ScoredCandidate]

---

### select_best_candidate

select_best_candidate(scored: list[ScoredCandidate]) -> AlbumCandidate | None

---

### verify_partial_acoustid

verify_partial_acoustid(tracks: list[str], candidate) -> float

- Returns match ratio (0.0 - 1.0)

---

### write_tags

write_tags(file_path: str, metadata: dict) -> None

---

## Rules

- All functions must be pure (no side effects except write_tags)
- All outputs must be JSON serializable