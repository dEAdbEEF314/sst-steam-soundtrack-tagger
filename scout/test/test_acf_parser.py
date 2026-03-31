"""Tests for acf_parser module."""
import pytest

from acf_parser import (
    get_app_id,
    get_install_dir,
    get_name,
    get_state_flags,
    is_installed,
    parse_acf,
)

# ---------------------------------------------------------------------------
# ACF fixtures
# ---------------------------------------------------------------------------

_INSTALLED_ACF = """\
"AppState"
{
\t"appid"\t\t"1234567"
\t"Universe"\t\t"1"
\t"name"\t\t"Victory Heat Rally- OST"
\t"StateFlags"\t\t"4"
\t"installdir"\t\t"Victory Heat Rally- OST"
\t"LastUpdated"\t\t"1700000000"
\t"SizeOnDisk"\t\t"512000000"
\t"BuildID"\t\t"99999"
}
"""

_UNINSTALLED_ACF = """\
"AppState"
{
\t"appid"\t\t"9999"
\t"name"\t\t"Some Game Soundtrack"
\t"StateFlags"\t\t"0"
\t"installdir"\t\t"SomeGame"
}
"""

_PARTIAL_INSTALL_ACF = """\
"AppState"
{
\t"appid"\t\t"8888"
\t"name"\t\t"Coffee Talk Soundtrack"
\t"StateFlags"\t\t"2"
\t"installdir"\t\t"CoffeeTalkOST"
}
"""


@pytest.fixture()
def installed_acf(tmp_path):
    p = tmp_path / "appmanifest_1234567.acf"
    p.write_text(_INSTALLED_ACF, encoding="utf-8")
    return str(p)


@pytest.fixture()
def uninstalled_acf(tmp_path):
    p = tmp_path / "appmanifest_9999.acf"
    p.write_text(_UNINSTALLED_ACF, encoding="utf-8")
    return str(p)


@pytest.fixture()
def partial_acf(tmp_path):
    p = tmp_path / "appmanifest_8888.acf"
    p.write_text(_PARTIAL_INSTALL_ACF, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_returns_app_state_dict(installed_acf):
    state = parse_acf(installed_acf)
    assert isinstance(state, dict)
    assert "appid" in state


def test_parse_appid_value(installed_acf):
    state = parse_acf(installed_acf)
    assert state["appid"] == "1234567"


def test_parse_name(installed_acf):
    state = parse_acf(installed_acf)
    assert state["name"] == "Victory Heat Rally- OST"


def test_get_app_id_returns_int(installed_acf):
    state = parse_acf(installed_acf)
    assert get_app_id(state) == 1234567


def test_get_name(installed_acf):
    state = parse_acf(installed_acf)
    assert get_name(state) == "Victory Heat Rally- OST"


def test_get_install_dir(installed_acf):
    state = parse_acf(installed_acf)
    assert get_install_dir(state) == "Victory Heat Rally- OST"


def test_get_state_flags_fully_installed(installed_acf):
    state = parse_acf(installed_acf)
    assert get_state_flags(state) == 4


def test_is_installed_true_for_fully_installed(installed_acf):
    state = parse_acf(installed_acf)
    assert is_installed(state) is True


def test_is_installed_false_for_not_installed(uninstalled_acf):
    state = parse_acf(uninstalled_acf)
    assert is_installed(state) is False


def test_is_installed_false_for_partial_install(partial_acf):
    """StateFlags=2 (UpdateRequired only, no FullyInstalled bit) → not installed."""
    state = parse_acf(partial_acf)
    assert is_installed(state) is False


def test_parse_raises_for_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_acf("/nonexistent/appmanifest_0.acf")


def test_parse_raises_value_error_for_missing_app_state(tmp_path):
    bad = tmp_path / "bad.acf"
    bad.write_text('"SomeOtherKey"\n{\n\t"x"\t"1"\n}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="AppState"):
        parse_acf(bad)
