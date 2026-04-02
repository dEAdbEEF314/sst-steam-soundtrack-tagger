# INTERFACES

## Data Types

### Track
- path: str
- duration: float | None

### AlbumCandidate
- mbid: str
- title: str
- artist: str | None
- track_count: int | None
- release_date: str | None
- score: float

### ScoredCandidate
- candidate: AlbumCandidate
- final_score: float

---

## Functions

### generate_fingerprint

generate_fingerprint(audio_path: str) -> tuple[int, str]

- Returns (duration, Chromaprint fingerprint)

---

### identify_track

identify_track(duration: int, fingerprint: str) -> dict | None

- Calls AcoustID API
- Returns best match result dict or None

---

### search_releases

search_releases(titles: list[str], limit: int = 5) -> list[AlbumCandidate]

- Queries MusicBrainz with multiple title variants
- Deduplicates by MBID

---

### score_candidates

score_candidates(candidates: list[AlbumCandidate], local_track_count: int, steam_release_date: str | None) -> list[AlbumCandidate]

---

### select_best_candidate

select_best_candidate(scored: list[ScoredCandidate]) -> AlbumCandidate | None

---

### partial_acoustid_verify

partial_acoustid_verify(files: list[str], candidate_title: str, partial_tracks: int, threshold: float) -> float

- Prefect task
- Returns match ratio (0.0 - 1.0)

---

### write_tags

write_tags(file_path: str, metadata: dict) -> None

- metadata keys: album, title, artist, track_number, total_tracks

---

## Rules

- All functions must be pure (no side effects except write_tags)
- All outputs must be JSON serializable