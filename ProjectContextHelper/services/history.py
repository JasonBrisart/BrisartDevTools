"""
Build History
Lightweight local record of completed Project Context Helper runs.
The previous version (v2.3.5) had this same history.py concept, but
HistoryEntry there had exactly 7 fields (created, root, profile,
export_dir, included_count, skipped_count, total_included_bytes) --
no git_branch or git_commit_short, since git state detection did not
exist at all in that version.
No external dependencies.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import sys

from core.constants import (
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
    git_branch: str = ""
    git_commit_short: str = ""


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


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
