from pathlib import Path

from models import AlbumCandidate
from pipeline.config import load_config
from scoring import score_candidates


def test_load_config_reads_storage_and_retry(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
retry:
  max_attempts: 4
  base_delay_sec: 7
acoustid:
  partial_verify_tracks: 2
  partial_match_threshold: 0.75
  full_fallback_min_match_ratio: 0.35
storage:
  endpoint_url: http://example.local
  bucket: buckets
  prefixes:
    ingest: ingest/
    archive: archive/
    review: review/
    workspace: workspace/
""".strip(),
        encoding="utf-8",
    )

    cfg = load_config(str(config))

    assert cfg.retry.max_attempts == 4
    assert cfg.retry.base_delay_sec == 7
    assert cfg.acoustid.partial_verify_tracks == 2
    assert cfg.acoustid.full_fallback_min_match_ratio == 0.35
    assert cfg.storage.bucket == "buckets"
    assert cfg.storage.archive_prefix == "archive/"


def test_score_candidates_prefers_track_count_and_date_match():
    candidates = [
        AlbumCandidate(mbid="1", title="A", track_count=31, release_date="2024-01-10"),
        AlbumCandidate(mbid="2", title="B", track_count=10, release_date="2020-01-10"),
    ]

    scored = score_candidates(
        candidates,
        local_track_count=31,
        steam_release_date="2024-01-15",
        tolerance_days=30,
    )

    assert scored[0].mbid == "1"
    assert scored[0].score > scored[1].score
