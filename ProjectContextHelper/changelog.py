"""
Changelog

Single source of truth for release history. Kept separate from
constants.py so release notes can evolve without touching core
configuration. The About tab reads from here, and the same data
can be written out to a CHANGELOG.md file for the repository.

No external dependencies.
"""
from __future__ import annotations

from pathlib import Path


# Full changelog — exact record of what changed, when, and how.
# Newest first.
#
# Each entry: (version, date, ( (change, how), ... ))
CHANGELOG = (
    (
        "2.1.5",
        "2026-07-26",
        (
            (
                "Combined the About and Updates tabs into one",
                "Removed gui/updates_tab.py and moved its controls into "
                "gui/about_tab.py; main_gui.py no longer creates a separate "
                "Updates tab.",
            ),
            (
                "Added automatic update check and download on startup",
                "updater.py gained resolve_download_url() and "
                "download_update(); the About tab runs the check ~500ms "
                "after launch when the startup toggle is enabled.",
            ),
            (
                "Updates are staged, not silently applied",
                "download_update() extracts the release into "
                "updates/v<version>/ (an excluded directory) and prompts for "
                "a restart instead of overwriting the running process.",
            ),
            (
                "Reduced updates settings to a single startup toggle",
                "Removed the manual 'Check for Updates' and 'Open Releases "
                "Page' buttons; only 'check on startup' remains.",
            ),
        ),
    ),
    (
        "2.1.4",
        "2026-07-26",
        (
            (
                "Made 'archive' the default profile",
                "Added DEFAULT_PROFILE = PROFILE_ARCHIVE in constants.py; the "
                "GUI Quick Export and the CLI --profile default now resolve "
                "to archive.",
            ),
            (
                "Removed the 'expanded' profile",
                "Dropped PROFILE_EXPANDED, apply_expanded_preset(), and the "
                "EXPANDED_* constants; VALID_PROFILES is now {standard, "
                "archive}.",
            ),
            (
                "Folded expanded-only extensions into archive",
                "The extra extensions (.rst, .log, .env.example, .sample, "
                ".template, .lock) were merged into ARCHIVE_EXTENSIONS so no "
                "coverage was lost.",
            ),
        ),
    ),
    (
        "2.1.3",
        "2026-07-26",
        (
            (
                "Centralized profile settings",
                "The GUI now reads per-profile values from "
                "settings_for_profile() instead of duplicating them, removing "
                "drift between constants.py and gui/builders.py.",
            ),
            (
                "Cleaned up the File Index table",
                "build_context_markdown() now builds columns dynamically so "
                "'Lines' and 'SHA256' only appear when their settings are "
                "enabled.",
            ),
            (
                "Hardened scan records and metadata",
                "Made FileRecord, SkipRecord, ScanResult, and BuildResult "
                "frozen; added a cached FileMeta and skip-reason constants in "
                "scanner.py.",
            ),
        ),
    ),
)


def latest_version() -> str:
    """
    Return the newest version string in the changelog, or "" if empty.
    """
    if not CHANGELOG:
        return ""
    return CHANGELOG[0][0]


def build_changelog_text() -> str:
    """
    Render the full changelog into readable plain text for the GUI.

    Format per release:
        vX.Y.Z - YYYY-MM-DD
          - <change>
              how: <how>
    """
    if not CHANGELOG:
        return "No changelog entries recorded."

    blocks: list[str] = []

    for version, date, changes in CHANGELOG:
        lines = [f"v{version} - {date}"]
        for change, how in changes:
            lines.append(f"  \u2022 {change}")
            lines.append(f"      how: {how}")
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def build_changelog_markdown() -> str:
    """
    Render the full changelog as Markdown for a CHANGELOG.md file.

    Format per release:
        ## vX.Y.Z - YYYY-MM-DD
        - **<change>**
          - how: <how>
    """
    lines: list[str] = ["# Changelog", ""]

    if not CHANGELOG:
        lines.append("_No changelog entries recorded._")
        return "\n".join(lines) + "\n"

    for version, date, changes in CHANGELOG:
        lines.append(f"## v{version} - {date}")
        lines.append("")
        for change, how in changes:
            lines.append(f"- **{change}**")
            lines.append(f"  - how: {how}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_changelog_markdown(
    path: Path | str = "CHANGELOG.md",
) -> Path:
    """
    Write the changelog out to a Markdown file and return its path.

    Keeps the repository's CHANGELOG.md in lockstep with the in-app
    changelog by regenerating from the same source data.
    """
    path = Path(path)
    path.write_text(
        build_changelog_markdown(),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    # Regenerate CHANGELOG.md from the source data.
    written = write_changelog_markdown()
    print(f"Wrote {written}")