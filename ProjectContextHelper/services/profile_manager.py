"""
Custom Profile Manager
Named, user-managed settings profiles with explicit Save / Load /
Delete actions. This module (and the entire Custom Profiles feature)
did not exist in the previous version of this tool (v2.3.5): there
was no custom_profiles.json, no --save-profile/--load-profile/
--delete-profile/--list-profiles CLI flags, and no custom_profile_var
anywhere in gui/builders.py's GuiState.
Distinct from the two built-in presets and from the automatic,
unnamed, always-on "last used settings" behavior in
services/settings_memory.py.
No external dependencies.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys

from core.constants import (
    CUSTOM_PROFILES_FILENAME,
    PROFILE_ARCHIVE,
    PROFILE_STANDARD,
)
from core.models import ScanSettings

RESERVED_PROFILE_NAMES = {PROFILE_STANDARD, PROFILE_ARCHIVE}


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def profiles_path(app_dir: Path | None = None) -> Path:
    return (app_dir or application_dir()) / CUSTOM_PROFILES_FILENAME


def is_reserved_name(name: str) -> bool:
    return name.strip().lower() in RESERVED_PROFILE_NAMES


def _load_all(app_dir: Path | None = None) -> dict[str, dict]:
    path = profiles_path(app_dir)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    profiles = raw.get("profiles")
    return profiles if isinstance(profiles, dict) else {}


def _save_all(profiles: dict[str, dict], app_dir: Path | None = None) -> None:
    path = profiles_path(app_dir)
    path.write_text(json.dumps({"profiles": profiles}, indent=2), encoding="utf-8")


def list_profiles(app_dir: Path | None = None) -> list[str]:
    return sorted(_load_all(app_dir).keys())


def profile_exists(name: str, app_dir: Path | None = None) -> bool:
    """
    Strips `name` before lookup, matching save_profile()'s behavior of
    always storing a stripped key.
    """
    return name.strip() in _load_all(app_dir)


def save_profile(name: str, settings: ScanSettings, app_dir: Path | None = None) -> None:
    name = name.strip()
    if not name:
        raise ValueError("Profile name cannot be empty.")
    if is_reserved_name(name):
        raise ValueError(f"'{name}' is a built-in profile name and cannot be used for a custom profile.")
    profiles = _load_all(app_dir)
    profiles[name] = settings.to_jsonable()
    _save_all(profiles, app_dir)


def load_profile(name: str, app_dir: Path | None = None) -> ScanSettings | None:
    """
    Strips `name` before lookup (see profile_exists() above for why).
    """
    raw = _load_all(app_dir).get(name.strip())
    if raw is None:
        return None
    try:
        return ScanSettings.from_jsonable(raw)
    except Exception:
        return None


def delete_profile(name: str, app_dir: Path | None = None) -> bool:
    """
    Strips `name` before lookup (see profile_exists() above for why).
    """
    name = name.strip()
    profiles = _load_all(app_dir)
    if name not in profiles:
        return False
    del profiles[name]
    _save_all(profiles, app_dir)
    return True
