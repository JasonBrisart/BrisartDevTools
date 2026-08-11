"""
Build History
Lightweight local record of completed Project Context Helper runs.
Stores a rolling history of successful builds (timestamp, project
root, profile, export folder, and basic counts) in a small JSON file
next to the application itself. The About tab reads from here to
show recent activity across every project the tool has been run
against.
No external dependencies.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import sys
from constants import (
    BUILD_HISTORY_FILENAME,
    MAX_HISTORY_ENTRIES,
)
@dataclass(frozen=True, slots=True)
class HistoryEntry:
    created: str
    root: str
    profile: str
    export_dir: str
    included_count: int
    skipped_count: int
    total_included_bytes: int
def application_dir() -> Path:
    """
    Return the directory the application package lives in.
    Mirrors updater.application_dir(); kept independent here so this
    module has no dependency on updater.py.
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
def history_path(
    app_dir: Path | None = None,
) -> Path:
    return (app_dir or application_dir()) / BUILD_HISTORY_FILENAME
def load_history(
    app_dir: Path | None = None,
) -> list[HistoryEntry]:
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
def save_history(
    entries: list[HistoryEntry],
    app_dir: Path | None = None,
) -> None:
    path = history_path(app_dir)
    path.write_text(
        json.dumps(
            [asdict(entry) for entry in entries],
            indent=2,
        ),
        encoding="utf-8",
    )
def append_history_entry(
    entry: HistoryEntry,
    app_dir: Path | None = None,
) -> list[HistoryEntry]:
    entries = load_history(app_dir)
    entries.insert(0, entry)
    entries = entries[:MAX_HISTORY_ENTRIES]
    save_history(entries, app_dir)
    return entries
def recent_entries(
    limit: int = 10,
    app_dir: Path | None = None,
) -> list[HistoryEntry]:
    return load_history(app_dir)[:limit]
def clear_history(
    app_dir: Path | None = None,
) -> None:
    save_history([], app_dir)
