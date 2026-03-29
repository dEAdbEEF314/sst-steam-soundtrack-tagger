Flow: SST Pipeline

Tasks:
- fetch_steam_metadata
- search_musicbrainz
- score_candidates
- partial_acoustid_verify
- full_acoustid_fallback
- write_tags