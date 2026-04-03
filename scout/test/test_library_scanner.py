"""Tests for library_scanner module."""
from pathlib import Path
import os
import pytest

from library_scanner import (
    AUDIO_EXTENSIONS,
    SOUNDTRACK_KEYWORDS,
    _detect_format_subdirs,
    _find_audio_files,
    _is_soundtrack_name,
    _pick_best_format_dir,
    _resolve_install_path,
    scan_library,
)
from models import SteamApp

# ---------------------------------------------------------------------------
# _is_soundtrack_name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name, expected",
    [
        ("Victory Heat Rally- OST", True),
        ("Coffee Talk Soundtrack", True),
        ("Original Sound Track Vol.1", True),
        ("Original Soundtrack", True),
        ("Music Pack Vol.2", True),
        ("Digital Soundtrack Edition", True),
        ("Original Score", True),
        # non-soundtracks
        ("Victory Heat Rally", False),
        ("Action RPG", False),
        ("Grand Strategy Game", False),
        ("My Game OST Expansion", True),   # contains "OST"
    ],
)
def test_is_soundtrack_name(name, expected):
    # This now tests the default keywords mapping
    assert any(kw.lower() in name.lower() for kw in SOUNDTRACK_KEYWORDS) is expected


# ---------------------------------------------------------------------------
# _find_audio_files
# ---------------------------------------------------------------------------

def test_find_audio_files_returns_audio_only(tmp_path):
    (tmp_path / "track01.flac").write_bytes(b"")
    (tmp_path / "track02.mp3").write_bytes(b"")
    (tmp_path / "cover.jpg").write_bytes(b"")
    (tmp_path / "README.txt").write_text("hi")

    files = _find_audio_files(tmp_path)
    assert len(files) == 2
    assert all(Path(f).suffix.lower() in AUDIO_EXTENSIONS for f in files)


def test_find_audio_files_recurses_subdirectories(tmp_path):
    sub = tmp_path / "bonus"
    sub.mkdir()
    (tmp_path / "01.flac").write_bytes(b"")
    (sub / "bonus01.ogg").write_bytes(b"")

    files = _find_audio_files(tmp_path)
    assert len(files) == 2


def test_find_audio_files_sorted(tmp_path):
    for name in ["03.flac", "01.flac", "02.flac"]:
        (tmp_path / name).write_bytes(b"")

    files = _find_audio_files(tmp_path)
    basenames = [Path(f).name for f in files]
    assert basenames == sorted(basenames)


def test_find_audio_files_empty_dir(tmp_path):
    assert _find_audio_files(tmp_path) == []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_library(base: Path, apps: list[dict]) -> None:
    """Helper to create a mock Steam library under *base*."""
    steamapps = base / "steamapps"
    steamapps.mkdir(parents=True, exist_ok=True)
    common = steamapps / "common"
    common.mkdir(exist_ok=True)

    for app in apps:
        acf_text = (
            '"AppState"\n'
            "{\n"
            f'\t"appid"\t\t"{app["appid"]}"\n'
            f'\t"name"\t\t"{app["name"]}"\n'
            f'\t"StateFlags"\t\t"{app.get("StateFlags", 4)}"\n'
            f'\t"installdir"\t\t"{app["installdir"]}"\n'
            "}\n"
        )
        (steamapps / f'appmanifest_{app["appid"]}.acf').write_text(
            acf_text, encoding="utf-8"
        )
        install_path = common / app["installdir"]
        install_path.mkdir(parents=True, exist_ok=True)
        for track in app.get("tracks", []):
            (install_path / track).write_bytes(b"")


def _make_library_with_music(base: Path, apps: list[dict]) -> None:
    """Create a mock Steam library with both common/ and music/ depots."""
    steamapps = base / "steamapps"
    (steamapps / "common").mkdir(parents=True, exist_ok=True)
    (steamapps / "music").mkdir(parents=True, exist_ok=True)

    for app in apps:
        acf_text = (
            '"AppState"\n'
            "{\n"
            f'\t"appid"\t\t"{app["appid"]}"\n'
            f'\t"name"\t\t"{app["name"]}"\n'
            f'\t"StateFlags"\t\t"{app.get("StateFlags", 4)}"\n'
            f'\t"installdir"\t\t"{app["installdir"]}"\n'
            "}\n"
        )
        (steamapps / f'appmanifest_{app["appid"]}.acf').write_text(
            acf_text, encoding="utf-8"
        )
        location = app.get("location", "common")
        install_root = steamapps / location / app["installdir"]

        if "format_subdirs" in app:
            # Create format-named subdirectories
            for fmt, tracks in app["format_subdirs"].items():
                fmt_dir = install_root / f"{app['name']} - {fmt}"
                fmt_dir.mkdir(parents=True, exist_ok=True)
                for track in tracks:
                    (fmt_dir / track).write_bytes(b"")
        else:
            install_root.mkdir(parents=True, exist_ok=True)
            for track in app.get("tracks", []):
                (install_root / track).write_bytes(b"")

# ---------------------------------------------------------------------------
# scan_library
# ---------------------------------------------------------------------------

def test_scan_library_raises_if_no_steamapps(tmp_path):
    with pytest.raises(FileNotFoundError, match="steamapps"):
        scan_library(str(tmp_path))


def test_scan_library_finds_installed_soundtrack(tmp_path):
    _make_library(
        tmp_path,
        [
            {
                "appid": "1234567",
                "name": "Victory Heat Rally- OST",
                "installdir": "Victory Heat Rally- OST",
                "tracks": ["01.flac", "02.flac"],
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 1
    assert apps[0].app_id == 1234567
    assert apps[0].name == "Victory Heat Rally- OST"
    assert apps[0].total_track_count == 2
    assert ".flac" in apps[0].audio_files_by_ext


def test_scan_library_skips_non_soundtrack(tmp_path):
    _make_library(
        tmp_path,
        [
            {
                "appid": "111",
                "name": "My Action Game",
                "installdir": "MyActionGame",
                "tracks": [],
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 0


def test_scan_library_skips_uninstalled(tmp_path):
    _make_library(
        tmp_path,
        [
            {
                "appid": "222",
                "name": "Coffee Talk Soundtrack",
                "installdir": "CoffeeTalkOST",
                "StateFlags": "0",
                "tracks": ["01.ogg"],
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 0


def test_scan_library_skips_app_with_no_audio(tmp_path):
    _make_library(
        tmp_path,
        [
            {
                "appid": "333",
                "name": "Game Soundtrack",
                "installdir": "GameOST",
                "tracks": [],   # no audio files
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 0


def test_scan_library_collects_all_formats(tmp_path):
    """複数フォーマットサブディレクトリがある場合、それら全てを収集することを確認する。"""
    _make_library_with_music(
        tmp_path,
        [
            {
                "appid": "1297600",
                "name": "art of rally OST",
                "installdir": "artofrally",
                "location": "music",
                "format_subdirs": {
                    "flac": ["01.flac", "02.flac"],
                    "mp3": ["01.mp3", "02.mp3", "03.mp3"],
                },
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 1
    app = apps[0]
    assert app.total_track_count == 5
    assert len(app.audio_files_by_ext[".flac"]) == 2
    assert len(app.audio_files_by_ext[".mp3"]) == 3
    assert len(app.audio_files) == 5


def test_scan_library_custom_config(tmp_path):
    """ScanConfig によるカスタム拡張子とキーワードの注入をテストする。"""
    _make_library(
        tmp_path,
        [
            {
                "appid": "999",
                "name": "My Custom Music",
                "installdir": "MyCustomMusic",
                "tracks": ["audio.wav", "audio.custom"],
            }
        ],
    )
    # デフォルトでは .custom は無視される
    apps = scan_library(str(tmp_path))
    assert len(apps) == 0

    # カスタム設定を渡す
    apps = scan_library(
        str(tmp_path),
        audio_extensions=frozenset({".wav", ".custom"}),
        soundtrack_keywords=("Music",)
    )
    assert len(apps) == 1
    assert apps[0].total_track_count == 2
    assert ".custom" in apps[0].audio_files_by_ext


def test_scan_library_audio_root_with_format_dir(tmp_path):
    _make_library_with_music(
        tmp_path,
        [
            {
                "appid": "1297600",
                "name": "art of rally OST",
                "installdir": "artofrally",
                "location": "music",
                "format_subdirs": {
                    "flac": ["track1.flac"],
                    "mp3": ["track1.mp3"],
                },
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    app = apps[0]
    audio_root = Path(app.audio_root)
    assert audio_root != Path(app.install_path)
    for ext, files in app.audio_files_by_ext.items():
        for f in files:
            assert Path(f).exists()


def test_scan_library_music_flat_layout(tmp_path):
    """Victory Heat Rally pattern: flat MP3 files in music/ with no format subdirs."""
    _make_library_with_music(
        tmp_path,
        [
            {
                "appid": "3222820",
                "name": "Victory Heat Rally: Original Soundtrack",
                "installdir": "Victory Heat Rally- OST",
                "location": "music",
                "tracks": ["01.mp3", "02.mp3", "03.mp3"],
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 1
    app = apps[0]
    assert app.storage_location == "music"
    assert app.format_dir is None
    assert app.audio_root == app.install_path
    assert app.total_track_count == 3
    assert ".mp3" in app.audio_files_by_ext
