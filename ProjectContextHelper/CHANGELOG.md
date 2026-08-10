# Changelog

## v2.1.5 - 2026-07-26

- **Combined the About and Updates tabs into one**
  - how: Removed gui/updates_tab.py and moved its controls into gui/about_tab.py; main_gui.py no longer creates a separate Updates tab.
- **Added automatic update check and download on startup**
  - how: updater.py gained resolve_download_url() and download_update(); the About tab runs the check ~500ms after launch when the startup toggle is enabled.
- **Updates are staged, not silently applied**
  - how: download_update() extracts the release into updates/v<version>/ (an excluded directory) and prompts for a restart instead of overwriting the running process.
- **Reduced updates settings to a single startup toggle**
  - how: Removed the manual 'Check for Updates' and 'Open Releases Page' buttons; only 'check on startup' remains.

## v2.1.4 - 2026-07-26

- **Made 'archive' the default profile**
  - how: Added DEFAULT_PROFILE = PROFILE_ARCHIVE in constants.py; the GUI Quick Export and the CLI --profile default now resolve to archive.
- **Removed the 'expanded' profile**
  - how: Dropped PROFILE_EXPANDED, apply_expanded_preset(), and the EXPANDED_* constants; VALID_PROFILES is now {standard, archive}.
- **Folded expanded-only extensions into archive**
  - how: The extra extensions (.rst, .log, .env.example, .sample, .template, .lock) were merged into ARCHIVE_EXTENSIONS so no coverage was lost.

## v2.1.3 - 2026-07-26

- **Centralized profile settings**
  - how: The GUI now reads per-profile values from settings_for_profile() instead of duplicating them, removing drift between constants.py and gui/builders.py.
- **Cleaned up the File Index table**
  - how: build_context_markdown() now builds columns dynamically so 'Lines' and 'SHA256' only appear when their settings are enabled.
- **Hardened scan records and metadata**
  - how: Made FileRecord, SkipRecord, ScanResult, and BuildResult frozen; added a cached FileMeta and skip-reason constants in scanner.py.
