"""Tests for library_scanner module."""
from pathlib import Path

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
    assert _is_soundtrack_name(name) is expected


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
# scan_library
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
    assert len(apps[0].audio_files) == 2


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


def test_scan_library_multiple_apps(tmp_path):
    _make_library(
        tmp_path,
        [
            {
                "appid": "1001",
                "name": "Game A Soundtrack",
                "installdir": "GameAST",
                "tracks": ["01.flac"],
            },
            {
                "appid": "1002",
                "name": "Regular Game",
                "installdir": "RegularGame",
                "tracks": ["game.exe"],
            },
            {
                "appid": "1003",
                "name": "Game B OST",
                "installdir": "GameBOST",
                "tracks": ["01.mp3", "02.mp3", "03.mp3"],
            },
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 2
    ids = {a.app_id for a in apps}
    assert ids == {1001, 1003}


# ---------------------------------------------------------------------------
# _resolve_install_path
# ---------------------------------------------------------------------------

def test_resolve_install_path_finds_music(tmp_path):
    music_dir = tmp_path / "steamapps" / "music" / "artofrally"
    music_dir.mkdir(parents=True)

    path, loc = _resolve_install_path(tmp_path / "steamapps", "artofrally")
    assert path == music_dir
    assert loc == "music"


def test_resolve_install_path_falls_back_to_common(tmp_path):
    common_dir = tmp_path / "steamapps" / "common" / "GameOST"
    common_dir.mkdir(parents=True)

    path, loc = _resolve_install_path(tmp_path / "steamapps", "GameOST")
    assert path == common_dir
    assert loc == "common"


def test_resolve_install_path_prefers_music_over_common(tmp_path):
    (tmp_path / "steamapps" / "music" / "GameOST").mkdir(parents=True)
    (tmp_path / "steamapps" / "common" / "GameOST").mkdir(parents=True)

    path, loc = _resolve_install_path(tmp_path / "steamapps", "GameOST")
    assert loc == "music"


def test_resolve_install_path_returns_none_when_missing(tmp_path):
    steamapps = tmp_path / "steamapps"
    steamapps.mkdir()

    path, loc = _resolve_install_path(steamapps, "nonexistent")
    assert path is None
    assert loc is None


# ---------------------------------------------------------------------------
# _detect_format_subdirs
# ---------------------------------------------------------------------------

def test_detect_format_subdirs_finds_flac_and_mp3(tmp_path):
    flac_dir = tmp_path / "Game OST - flac"
    mp3_dir = tmp_path / "Game OST - mp3"
    flac_dir.mkdir()
    mp3_dir.mkdir()
    (flac_dir / "01.flac").write_bytes(b"")
    (mp3_dir / "01.mp3").write_bytes(b"")

    result = _detect_format_subdirs(tmp_path)
    assert "flac" in result
    assert "mp3" in result
    assert result["flac"] == flac_dir
    assert result["mp3"] == mp3_dir


def test_detect_format_subdirs_ignores_empty_subdirs(tmp_path):
    empty_flac = tmp_path / "Game OST - flac"
    empty_flac.mkdir()

    result = _detect_format_subdirs(tmp_path)
    assert "flac" not in result


def test_detect_format_subdirs_returns_empty_for_flat_layout(tmp_path):
    (tmp_path / "01.flac").write_bytes(b"")
    (tmp_path / "02.flac").write_bytes(b"")

    result = _detect_format_subdirs(tmp_path)
    assert result == {}


def test_detect_format_subdirs_finds_nested_audio(tmp_path):
    flac_root = tmp_path / "Game OST - flac"
    disc1 = flac_root / "Disc 1"
    disc1.mkdir(parents=True)
    (disc1 / "01.flac").write_bytes(b"")

    result = _detect_format_subdirs(tmp_path)
    assert result["flac"] == flac_root


def test_detect_format_subdirs_prefers_dir_with_more_files(tmp_path):
    flac_a = tmp_path / "Game OST - flac"
    flac_b = tmp_path / "Game OST Bonus flac"
    flac_a.mkdir()
    flac_b.mkdir()
    (flac_a / "01.flac").write_bytes(b"")
    (flac_b / "01.flac").write_bytes(b"")
    (flac_b / "02.flac").write_bytes(b"")

    result = _detect_format_subdirs(tmp_path)
    assert result["flac"] == flac_b


# ---------------------------------------------------------------------------
# _pick_best_format_dir
# ---------------------------------------------------------------------------

def test_pick_best_prefers_flac_over_mp3(tmp_path):
    format_dirs = {
        "mp3": tmp_path / "mp3",
        "flac": tmp_path / "flac",
    }
    fmt, path = _pick_best_format_dir(format_dirs)
    assert fmt == "flac"


def test_pick_best_falls_back_when_flac_absent(tmp_path):
    format_dirs = {"ogg": tmp_path / "ogg", "mp3": tmp_path / "mp3"}
    fmt, path = _pick_best_format_dir(format_dirs)
    assert fmt == "ogg"


def test_pick_best_returns_none_for_empty(tmp_path):
    assert _pick_best_format_dir({}) is None


# ---------------------------------------------------------------------------
# scan_library — music/ and format_dir integration
# ---------------------------------------------------------------------------

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


def test_scan_library_finds_music_depot(tmp_path):
    _make_library_with_music(
        tmp_path,
        [
            {
                "appid": "1297600",
                "name": "art of rally OST",
                "installdir": "artofrally",
                "location": "music",
                "tracks": ["01.flac", "02.flac"],
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 1
    assert apps[0].storage_location == "music"
    assert apps[0].format_dir is None
    assert len(apps[0].audio_files) == 2


def test_scan_library_selects_flac_format_subdir(tmp_path):
    _make_library_with_music(
        tmp_path,
        [
            {
                "appid": "1297600",
                "name": "art of rally OST",
                "installdir": "artofrally",
                "location": "music",
                "format_subdirs": {
                    "flac": ["01.flac", "02.flac", "03.flac"],
                    "mp3": ["01.mp3", "02.mp3", "03.mp3"],
                },
            }
        ],
    )
    apps = scan_library(str(tmp_path))
    assert len(apps) == 1
    app = apps[0]
    assert app.storage_location == "music"
    assert app.format_dir is not None
    assert "flac" in app.format_dir.lower()
    assert all(f.endswith(".flac") for f in app.audio_files)
    assert len(app.audio_files) == 3


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
    # audio_root should be install_path / format_dir
    assert audio_root != Path(app.install_path)
    # All audio_files should be relative to audio_root
    for f in app.audio_files:
        assert Path(f).is_relative_to(audio_root)


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
    assert len(app.audio_files) == 3
