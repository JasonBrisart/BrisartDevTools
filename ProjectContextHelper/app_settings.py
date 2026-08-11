"""
Application Settings
Persists the app-level GUI preference toggles (as opposed to
per-export scan settings, which are recorded separately in each
export's PROJECT_CONTEXT_SETTINGS.json). Stores them in a small JSON
file next to the application itself, so choices like "check for
updates on startup" and "automatically install updates" survive
between launches — including when running as a compiled .exe.
No external dependencies.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import sys
from constants import APP_SETTINGS_FILENAME
@dataclass(slots=True)
class AppPreferences:
    """
    App-level GUI preferences that persist across launches.
    """
    open_after_build: bool = False
    check_updates_startup: bool = False
    auto_install_updates: bool = False
def application_dir() -> Path:
    """
    Return the directory the application package lives in.
    Mirrors updater.application_dir() and history.application_dir();
    kept independent here so this module has no dependency on either.
    When running as a normal Python script, this is the folder
    containing this module. When running as a frozen PyInstaller
    executable — especially a --onefile build — __file__ instead
    resolves to a temporary extraction folder (sys._MEIPASS) that
    PyInstaller deletes the moment the process exits, so anything
    written there would silently vanish every run. In frozen mode
    this returns the folder containing the actual .exe file instead,
    which persists across launches.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent
def settings_path(
    app_dir: Path | None = None,
) -> Path:
    return (app_dir or application_dir()) / APP_SETTINGS_FILENAME
def load_preferences(
    app_dir: Path | None = None,
) -> AppPreferences:
    """
    Load saved app preferences, or return defaults if no settings
    file exists yet, or if it cannot be parsed (e.g. corrupted by an
    external edit).
    """
    path = settings_path(app_dir)
    if not path.exists():
        return AppPreferences()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return AppPreferences()
    defaults = AppPreferences()
    return AppPreferences(
        open_after_build=bool(
            raw.get("open_after_build", defaults.open_after_build)
        ),
        check_updates_startup=bool(
            raw.get(
                "check_updates_startup",
                defaults.check_updates_startup,
            )
        ),
        auto_install_updates=bool(
            raw.get(
                "auto_install_updates",
                defaults.auto_install_updates,
            )
        ),
    )
def save_preferences(
    preferences: AppPreferences,
    app_dir: Path | None = None,
) -> None:
    """
    Write app preferences to disk. Called whenever a preference
    toggle changes, so the on-disk file always reflects the last
    choice the user made, without needing an explicit "save" action
    or a clean shutdown.
    """
    path = settings_path(app_dir)
    path.write_text(
        json.dumps(asdict(preferences), indent=2),
        encoding="utf-8",
    )