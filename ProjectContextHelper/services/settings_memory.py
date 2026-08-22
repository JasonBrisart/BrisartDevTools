"""
Settings Memory
Always-on GUI behavior: every successful GUI build silently saves the
settings used, and every GUI launch silently loads them back in place
of the selected profile's plain defaults. No toggle exists for this.
This module did not exist in the previous version of this tool
(v2.3.5): that version's app_settings.py had exactly three
AppPreferences fields (open_after_build, check_updates_startup,
auto_install_updates) and no concept of remembering export settings
across launches at all -- every launch always started from the
selected profile's plain defaults.
Distinct from services/profile_manager.py's named, multi-slot Custom
Profiles.
No external dependencies.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys

from core.constants import LAST_SETTINGS_FILENAME
from core.models import ScanSettings


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def last_settings_path(app_dir: Path | None = None) -> Path:
    return (app_dir or application_dir()) / LAST_SETTINGS_FILENAME


def save_last_settings(settings: ScanSettings, app_dir: Path | None = None) -> None:
    try:
        path = last_settings_path(app_dir)
        path.write_text(json.dumps(settings.to_jsonable(), indent=2), encoding="utf-8")
    except Exception:
        pass


def load_last_settings(app_dir: Path | None = None) -> ScanSettings | None:
    path = last_settings_path(app_dir)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    try:
        return ScanSettings.from_jsonable(raw)
    except Exception:
        return None


def clear_last_settings(app_dir: Path | None = None) -> None:
    path = last_settings_path(app_dir)
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
