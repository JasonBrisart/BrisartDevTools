"""
Storage
Single consolidated module for every piece of persisted application
state that is not part of a build's own output files.

Before this module existed, this same functionality was spread across
four separate files:
  - services/app_settings.py    -- AppPreferences        (app_settings.json)
  - services/settings_memory.py -- always-on last-used   (last_export_settings.json)
  - services/profile_manager.py -- named Custom Profiles (custom_profiles.json)
  - services/history.py         -- build history          (build_history.json)
Each of those four files had its own near-identical application_dir()
helper, independently re-implementing the same frozen-vs-source
resolution logic. That duplication is exactly the kind of thing that
lets small inconsistencies creep in over time. All four are now gone;
everything below lives in this one file instead.

Every other module in this app that needs to read or write any of
this state (core/builder.py, cli/cli.py, gui/builders.py,
gui/profiles_section.py, gui/about_tab.py) imports directly from
services.storage and nowhere else. No module outside this file
performs its own file I/O against app_settings.json,
last_export_settings.json, custom_profiles.json, or
build_history.json.

Sections in this file, each self-contained but sharing the same
application_dir() helper:
  1. Shared application_dir() helper
  2. App Preferences      (app_settings.json)
  3. Last Used Settings   (last_export_settings.json) -- always-on GUI memory
  4. Custom Profiles      (custom_profiles.json)       -- named, explicit Save/Load/Delete
  5. Build History        (build_history.json)         -- Recent Exports list

No external dependencies.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import sys

from core.constants import (
    APP_SETTINGS_FILENAME,
    BUILD_HISTORY_FILENAME,
    CUSTOM_PROFILES_FILENAME,
    LAST_SETTINGS_FILENAME,
    MAX_HISTORY_ENTRIES,
    PROFILE_ARCHIVE,
    PROFILE_STANDARD,
)
from core.models import ScanSettings


# ============================================================
# 1. Shared application_dir() helper
# ============================================================
def application_dir() -> Path:
    """
    Return the application's root folder (the one containing run.py),
    not the services/ folder this module itself lives in.
    When frozen (PyInstaller), this is the folder containing the
    compiled .exe. When running from source, this module sits at
    <app_root>/services/storage.py, so the app root is one level
    above this file's own parent directory.
    This is the single implementation of this resolution logic used
    by every kind of persisted state in this file -- previously each
    of the four modules this file replaces had its own copy of this
    exact function.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


# ============================================================
# 2. App Preferences (app_settings.json)
# Remaining user-controlled GUI preference toggles: open export
# folder after build, check for updates on startup, auto-install
# downloaded updates.
# ============================================================
@dataclass(slots=True)
class AppPreferences:
    open_after_build: bool = False
    check_updates_startup: bool = False
    auto_install_updates: bool = False


def app_settings_path(app_dir: Path | None = None) -> Path:
    return (app_dir or application_dir()) / APP_SETTINGS_FILENAME


def load_preferences(app_dir: Path | None = None) -> AppPreferences:
    path = app_settings_path(app_dir)
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
    path = app_settings_path(app_dir)
    path.write_text(json.dumps(asdict(preferences), indent=2), encoding="utf-8")


# ============================================================
# 3. Last Used Settings (last_export_settings.json)
# Always-on GUI behavior: every successful GUI build silently saves
# the settings used, and every GUI launch silently loads them back in
# place of the selected profile's plain defaults. No toggle exists
# for this in the GUI. The CLI's --remember-settings/--use-last-settings
# flags read/write this same file but remain explicit opt-in, since
# CLI invocations are typically scripted and expected to stay
# deterministic unless a user explicitly asks otherwise.
# Distinct from Custom Profiles below (named, multi-slot, explicit).
# ============================================================
def last_settings_path(app_dir: Path | None = None) -> Path:
    return (app_dir or application_dir()) / LAST_SETTINGS_FILENAME


def save_last_settings(settings: ScanSettings, app_dir: Path | None = None) -> None:
    """
    Any failure here is swallowed rather than raised -- this is a
    convenience feature and must never cause an otherwise-successful
    build to fail or surface an error dialog to the user.
    """
    try:
        path = last_settings_path(app_dir)
        path.write_text(json.dumps(settings.to_jsonable(), indent=2), encoding="utf-8")
    except Exception:
        pass


def load_last_settings(app_dir: Path | None = None) -> ScanSettings | None:
    """
    Returns None when no file exists yet, or when it can't be parsed
    into a valid ScanSettings -- callers should fall back to the
    selected profile's normal defaults rather than raising.
    """
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
    """
    Remove any saved settings memory. Not called automatically by the
    GUI (there's no toggle to turn off); kept available for
    scripting/manual use.
    """
    path = last_settings_path(app_dir)
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


# ============================================================
# 4. Custom Profiles (custom_profiles.json)
# Named, user-managed settings profiles with explicit Save / Load /
# Delete actions. Distinct from the two built-in presets ("standard",
# "archive" -- reserved names, can't be used for a custom profile)
# and from the automatic, unnamed Last Used Settings above.
# ============================================================
RESERVED_PROFILE_NAMES = {PROFILE_STANDARD, PROFILE_ARCHIVE}


def profiles_path(app_dir: Path | None = None) -> Path:
    return (app_dir or application_dir()) / CUSTOM_PROFILES_FILENAME


def is_reserved_name(name: str) -> bool:
    return name.strip().lower() in RESERVED_PROFILE_NAMES


def _load_all_profiles(app_dir: Path | None = None) -> dict[str, dict]:
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


def _save_all_profiles(profiles: dict[str, dict], app_dir: Path | None = None) -> None:
    path = profiles_path(app_dir)
    path.write_text(json.dumps({"profiles": profiles}, indent=2), encoding="utf-8")


def list_profiles(app_dir: Path | None = None) -> list[str]:
    return sorted(_load_all_profiles(app_dir).keys())


def profile_exists(name: str, app_dir: Path | None = None) -> bool:
    """
    Strips `name` before lookup, matching save_profile()'s behavior
    of always storing a stripped key, so a name with incidental
    leading/trailing whitespace still resolves to the same profile.
    """
    return name.strip() in _load_all_profiles(app_dir)


def save_profile(name: str, settings: ScanSettings, app_dir: Path | None = None) -> None:
    name = name.strip()
    if not name:
        raise ValueError("Profile name cannot be empty.")
    if is_reserved_name(name):
        raise ValueError(f"'{name}' is a built-in profile name and cannot be used for a custom profile.")
    profiles = _load_all_profiles(app_dir)
    profiles[name] = settings.to_jsonable()
    _save_all_profiles(profiles, app_dir)


def load_profile(name: str, app_dir: Path | None = None) -> ScanSettings | None:
    """
    Strips `name` before lookup (see profile_exists() above for why).
    """
    raw = _load_all_profiles(app_dir).get(name.strip())
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
    profiles = _load_all_profiles(app_dir)
    if name not in profiles:
        return False
    del profiles[name]
    _save_all_profiles(profiles, app_dir)
    return True


# ============================================================
# 5. Build History (build_history.json)
# Lightweight local record of completed builds, shown as the Recent
# Exports list on the About tab.
# ============================================================
@dataclass(frozen=True, slots=True)
class HistoryEntry:
    created: str
    root: str
    profile: str
    export_dir: str
    included_count: int
    skipped_count: int
    total_included_bytes: int
    git_branch: str = ""
    git_commit_short: str = ""


def history_path(app_dir: Path | None = None) -> Path:
    return (app_dir or application_dir()) / BUILD_HISTORY_FILENAME


def load_history(app_dir: Path | None = None) -> list[HistoryEntry]:
    path = history_path(app_dir)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    entries: list[HistoryEntry] = []
    for item in raw:
        try:
            entries.append(HistoryEntry(**item))
        except TypeError:
            continue
    return entries


def save_history(entries: list[HistoryEntry], app_dir: Path | None = None) -> None:
    path = history_path(app_dir)
    path.write_text(json.dumps([asdict(e) for e in entries], indent=2), encoding="utf-8")


def append_history_entry(entry: HistoryEntry, app_dir: Path | None = None) -> list[HistoryEntry]:
    entries = load_history(app_dir)
    entries.insert(0, entry)
    entries = entries[:MAX_HISTORY_ENTRIES]
    save_history(entries, app_dir)
    return entries


def recent_entries(limit: int = 10, app_dir: Path | None = None) -> list[HistoryEntry]:
    return load_history(app_dir)[:limit]


def clear_history(app_dir: Path | None = None) -> None:
    save_history([], app_dir)
