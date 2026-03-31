"""Parse Steam ACF (App Cache File) manifests in Valve Data Format (VDF)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import vdf

logger = logging.getLogger(__name__)


def parse_acf(acf_path: str | Path) -> dict[str, Any]:
    """Parse a Steam ACF file and return the ``AppState`` dict.

    Raises ``ValueError`` if the file does not contain an ``AppState`` key.
    """
    with open(acf_path, encoding="utf-8", errors="replace") as fh:
        data = vdf.load(fh)
    app_state = data.get("AppState")
    if app_state is None:
        raise ValueError(f"No 'AppState' key in {acf_path}")
    return app_state


def get_app_id(app_state: dict[str, Any]) -> int | None:
    """Return the integer appid, or None if absent/invalid."""
    try:
        return int(app_state["appid"])
    except (KeyError, ValueError, TypeError):
        return None


def get_name(app_state: dict[str, Any]) -> str:
    return str(app_state.get("name", ""))


def get_install_dir(app_state: dict[str, Any]) -> str:
    return str(app_state.get("installdir", ""))


def get_state_flags(app_state: dict[str, Any]) -> int:
    try:
        return int(app_state.get("StateFlags", 0))
    except (ValueError, TypeError):
        return 0


def is_installed(app_state: dict[str, Any]) -> bool:
    """Return True if the FullyInstalled bit (0x4) is set in StateFlags."""
    return (get_state_flags(app_state) & 4) != 0
