"""
Application Settings
Persists the app-level GUI preference toggles that remain
user-controlled: open export folder after build, check for updates
on startup, auto-install downloaded updates.
No external dependencies.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import sys

from core.constants import APP_SETTINGS_FILENAME


@dataclass(slots=True)
class AppPreferences:
    open_after_build: bool = False
    check_updates_startup: bool = False
    auto_install_updates: bool = False


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def settings_path(app_dir: Path | None = None) -> Path:
    return (app_dir or application_dir()) / APP_SETTINGS_FILENAME


def load_preferences(app_dir: Path | None = None) -> AppPreferences:
    path = settings_path(app_dir)
    if not path.exists():
        return AppPreferences()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return AppPreferences()
    defaults = AppPreferences()
    return AppPreferences(
        open_after_build=bool(raw.get("open_after_build", defaults.open_after_build)),
        check_updates_startup=bool(raw.get("check_updates_startup", defaults.check_updates_startup)),
        auto_install_updates=bool(raw.get("auto_install_updates", defaults.auto_install_updates)),
    )


def save_preferences(preferences: AppPreferences, app_dir: Path | None = None) -> None:
    path = settings_path(app_dir)
    path.write_text(json.dumps(asdict(preferences), indent=2), encoding="utf-8")
