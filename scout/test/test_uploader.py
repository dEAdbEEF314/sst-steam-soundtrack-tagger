"""Tests for uploader module."""
import json
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from models import SteamApp, UploadResult
from uploader import upload_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def steam_app(tmp_path) -> SteamApp:
    install_path = tmp_path / "Victory Heat Rally- OST"
    install_path.mkdir()
    track1 = install_path / "01 - Opening.flac"
    track2 = install_path / "02 - Victory.flac"
    track1.write_bytes(b"FAKE_FLAC_DATA_1")
    track2.write_bytes(b"FAKE_FLAC_DATA_2")

    acf = tmp_path / "appmanifest_1234567.acf"
    acf.write_text(
        '"AppState"\n{\n\t"appid"\t"1234567"\n\t"name"\t"Victory Heat Rally- OST"\n}\n'
    )
    return SteamApp(
        app_id=1234567,
        name="Victory Heat Rally- OST",
        install_dir="Victory Heat Rally- OST",
        install_path=str(install_path),
        acf_path=str(acf),
        audio_files_by_ext={".flac": [str(track1), str(track2)]},
    )


@pytest.fixture()
def steam_app_with_format_dir(tmp_path) -> SteamApp:
    install_root = tmp_path / "artofrally"
    flac_dir = install_root / "art of rally OST - flac"
    flac_dir.mkdir(parents=True)
    track1 = flac_dir / "01 - avalanche.flac"
    track2 = flac_dir / "02 - barriers.flac"
    track1.write_bytes(b"FAKE_FLAC_DATA_1")
    track2.write_bytes(b"FAKE_FLAC_DATA_2")

    acf = tmp_path / "appmanifest_1297600.acf"
    acf.write_text(
        '"AppState"\n{\n\t"appid"\t"1297600"\n\t"name"\t"art of rally OST"\n}\n'
    )
    return SteamApp(
        app_id=1297600,
        name="art of rally OST",
        install_dir="artofrally",
        install_path=str(install_root),
        acf_path=str(acf),
        storage_location="music",
        format_dir="art of rally OST - flac",
        audio_files_by_ext={".flac": [str(track1), str(track2)]},
    )


# ---------------------------------------------------------------------------
# Dry-run tests (no S3 calls)
# ---------------------------------------------------------------------------

def test_dry_run_does_not_call_s3(steam_app):
    mock_s3 = MagicMock()
    upload_app(mock_s3, "buckets", steam_app, dry_run=True, upload_audio=True)

    mock_s3.upload_file.assert_not_called()
    mock_s3.put_object.assert_not_called()


def test_dry_run_returns_upload_result(steam_app):
    result = upload_app(None, "buckets", steam_app, dry_run=True)
    assert isinstance(result, UploadResult)
    assert result.dry_run is True


def test_dry_run_app_id(steam_app):
    result = upload_app(None, "buckets", steam_app, dry_run=True)
    assert result.app_id == 1234567


# ---------------------------------------------------------------------------
# Key format tests
# ---------------------------------------------------------------------------

def test_acf_key_format(steam_app):
    result = upload_app(None, "buckets", steam_app, dry_run=True)
    assert result.acf_key == "ingest/1234567/manifest.acf"


def test_file_keys_contain_extension_dir(steam_app):
    result = upload_app(None, "buckets", steam_app, dry_run=True, upload_audio=True)
    # result.file_keys should look like ingest/1234567/Disc 1/flac/01 - Opening.flac
    assert all(k.startswith("ingest/1234567/Disc 1/flac/") for k in result.file_keys)


def test_file_keys_contain_track_names(steam_app):
    result = upload_app(None, "buckets", steam_app, dry_run=True, upload_audio=True)
    names = [Path(k).name for k in result.file_keys]
    assert "01 - Opening.flac" in names
    assert "02 - Victory.flac" in names


def test_file_key_count(steam_app):
    result = upload_app(None, "buckets", steam_app, dry_run=True, upload_audio=True)
    assert len(result.file_keys) == 2


def test_scout_result_key_format(steam_app):
    result = upload_app(None, "buckets", steam_app, dry_run=True)
    assert result.scout_result_key == "ingest/1234567/scout_result.json"


# ---------------------------------------------------------------------------
# Path Normalization and Structure Tests
# ---------------------------------------------------------------------------

def test_redundant_format_dir_stripping_and_disc_completion(tmp_path):
    """'FLAC/01.flac' should become 'Disc 1/flac/01.flac'."""
    install_path = tmp_path / "Game OST"
    flac_dir = install_path / "FLAC"
    flac_dir.mkdir(parents=True)
    track = flac_dir / "01.flac"
    track.write_bytes(b"")

    app = SteamApp(
        app_id=100,
        name="Game OST",
        install_dir="GameOST",
        install_path=str(install_path),
        acf_path="fake.acf",
        audio_files_by_ext={".flac": [str(track)]},
    )
    result = upload_app(None, "buckets", app, dry_run=True, upload_audio=True)
    assert result.file_keys[0] == "ingest/100/Disc 1/flac/01.flac"


def test_internal_dir_moved_before_extension(tmp_path):
    """'Disc 2/01.flac' should become 'Disc 2/flac/01.flac'."""
    install_path = tmp_path / "Big OST"
    disc_dir = install_path / "Disc 2"
    disc_dir.mkdir(parents=True)
    track = disc_dir / "01.flac"
    track.write_bytes(b"")

    app = SteamApp(
        app_id=200,
        name="Big OST",
        install_dir="BigOST",
        install_path=str(install_path),
        acf_path="fake.acf",
        audio_files_by_ext={".flac": [str(track)]},
    )
    result = upload_app(None, "buckets", app, dry_run=True, upload_audio=True)
    # Expected ingest/200/Disc 2/flac/01.flac
    assert result.file_keys[0] == "ingest/200/Disc 2/flac/01.flac"


def test_complex_normalization_with_existing_disc(tmp_path):
    """'Disc 2/FLAC/01.flac' should become 'Disc 2/flac/01.flac'."""
    install_path = tmp_path / "Mix"
    complex_dir = install_path / "Disc 2" / "FLAC"
    complex_dir.mkdir(parents=True)
    track = complex_dir / "01.flac"
    track.write_bytes(b"")

    app = SteamApp(
        app_id=300,
        name="Mix",
        install_dir="Mix",
        install_path=str(install_path),
        acf_path="fake.acf",
        audio_files_by_ext={".flac": [str(track)]},
    )
    result = upload_app(None, "buckets", app, dry_run=True, upload_audio=True)
    assert result.file_keys[0] == "ingest/300/Disc 2/flac/01.flac"


# ---------------------------------------------------------------------------
# no_audio flag
# ---------------------------------------------------------------------------

def test_no_audio_produces_empty_file_keys(steam_app):
    result = upload_app(None, "buckets", steam_app, dry_run=True, upload_audio=False)
    assert result.file_keys == []


def test_no_audio_does_not_call_upload_file_for_audio(steam_app):
    mock_s3 = MagicMock()
    # Mocking upload_file to avoid real FS access if any, though _upload_file is tested elsewhere
    upload_app(mock_s3, "buckets", steam_app, dry_run=False, upload_audio=False)
    
    # upload_file should be called for ACF, but NOT for audio tracks
    for c in mock_s3.upload_file.call_args_list:
        key = c.args[2] if len(c.args) >= 3 else c.kwargs.get("Key", "")
        # Extension dirs should not be in keys when upload_audio=False
        assert not any(f"/{ext.lstrip('.')}/" in key for ext in steam_app.audio_files_by_ext)


# ---------------------------------------------------------------------------
# Real (non-dry-run) S3 call shape
# ---------------------------------------------------------------------------

def test_real_upload_calls_put_object_for_result(steam_app):
    mock_s3 = MagicMock()
    upload_app(mock_s3, "buckets", steam_app, dry_run=False, upload_audio=False)

    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "buckets"
    assert call_kwargs["Key"] == "ingest/1234567/scout_result.json"
    assert call_kwargs["ContentType"] == "application/json"

    # Verify the body is valid JSON with expected fields
    body = json.loads(call_kwargs["Body"].decode("utf-8"))
    assert body["app_id"] == 1234567
    assert body["name"] == "Victory Heat Rally- OST"
    assert "uploaded_at" in body
    assert "files_by_ext" in body
    assert "flac" in body["files_by_ext"]


def test_real_upload_calls_upload_file_for_acf(steam_app):
    mock_s3 = MagicMock()
    upload_app(mock_s3, "buckets", steam_app, dry_run=False, upload_audio=False)

    # The ACF upload goes via upload_file
    upload_file_calls = mock_s3.upload_file.call_args_list
    acf_calls = [c for c in upload_file_calls if c.args[2] == "ingest/1234567/manifest.acf"]
    assert len(acf_calls) == 1


def test_scout_result_includes_location_and_file_stats(steam_app_with_format_dir):
    mock_s3 = MagicMock()
    upload_app(mock_s3, "buckets", steam_app_with_format_dir, dry_run=False, upload_audio=True)

    call_kwargs = mock_s3.put_object.call_args.kwargs
    body = json.loads(call_kwargs["Body"].decode("utf-8"))
    assert body["storage_location"] == "music"
    assert "flac" in body["files_by_ext"]
    assert body["files_by_ext"]["flac"]["count"] == 2
    assert len(body["files_by_ext"]["flac"]["keys"]) == 2


# ---------------------------------------------------------------------------
# check_already_processed
# ---------------------------------------------------------------------------

def test_check_already_processed_exists():
    from uploader import check_already_processed
    mock_s3 = MagicMock()
    # head_object succeeds -> exists
    mock_s3.head_object.return_value = {}
    
    assert check_already_processed(mock_s3, "buckets", 123) is True
    mock_s3.head_object.assert_called_with(Bucket="buckets", Key="ingest/123/scout_result.json")


def test_check_already_processed_missing():
    from uploader import check_already_processed
    mock_s3 = MagicMock()
    mock_s3.head_object.side_effect = Exception("Not Found")
    
    assert check_already_processed(mock_s3, "buckets", 123) is False
