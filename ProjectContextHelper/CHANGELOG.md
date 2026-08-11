# Changelog

All notable changes to Project Context Helper are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.1] - 2026-08-11

### Fixed

- **Update check could select another tool's release in the BrisartDevTools monorepo.** `check_for_updates()` previously queried GitHub's `/releases/latest` endpoint, which returns the newest release for the entire `BrisartDevTools` repository rather than the newest Project Context Helper release specifically. Since the repo also contains independently versioned tools (CanonSync, AutoExeBuilder, ReadmeBuilder, ReleaseNoteBuilder), publishing a release for any other tool after the latest Project Context Helper release would cause the updater to detect, download, and apply that other tool's release instead.
- **Update checks now filter the full releases list by tag prefix.** `constants.py` replaces `UPDATE_CHECK_URL` with `RELEASES_LIST_URL` (the full `/releases` list) and a new `RELEASE_TAG_PREFIX = "project-context-helper-v"`. `updater.py` gained `find_latest_release_payload()`, which walks the list and returns the first release whose tag actually starts with that prefix, ignoring newer releases belonging to other tools in the repo.

### Notes

- If no release matching the tag prefix is found (e.g. the prefix convention changes, or no Project Context Helper release exists yet), `check_for_updates()` now reports this explicitly instead of silently falling back to an unrelated release.
- Verified with a simulated monorepo releases list (`canonsync-v1.2.0` listed as newest, `project-context-helper-v2.2.0` and `-v2.1.5` behind it): confirmed the old `/releases/latest`-style logic would have selected the CanonSync release, and confirmed the fixed filtering logic correctly selects the matching Project Context Helper release instead.

## [2.2.0] - 2026-08-11

### Added

- **Real in-place auto-updater.** `updater.py` gained `find_release_root()`, `backup_application()`, `apply_extracted_update()`, `apply_staged_update()`, and `install_update()`. Together these extract a downloaded release and overwrite the running application's own files, rather than only staging the download as before.
- **Every in-place update is backed up first.** `backup_application()` copies the current application files into `updates/backups/v<version>_<timestamp>/` before `apply_extracted_update()` overwrites anything, so a bad update can be reversed manually.
- **CLI `--install-updates` flag.** Downloads, backs up, and applies an available update from the command line in one step (implies `--check-updates`).

### Changed

- **Auto-install is a separate, opt-in toggle.** Added `GuiState.auto_install_var`, defaulting to off. The existing "check for updates on startup" toggle still only downloads and stages by default; auto-install must be enabled separately before a staged update is applied over the running files.
- **Updater never touches its own staging or export folders.** Introduced a shared `PROTECTED_NAMES` set (`updates/`, `PROJECT_CONTEXT_EXPORTS/`, `__pycache__`, `.git`, `download.zip`) that both the backup step and the apply step exclude.

### Notes

- In-place updates are overwrite-only: files present in the application directory but absent from the release are left untouched, never deleted.
- Verified functionally before shipping: GitHub zipball wrapper unwrapping, flat packaged-release layout, backup content correctness, and `PROTECTED_NAMES` exclusion were each tested directly.

## [2.1.5] - 2026-07-26

### Added

- **Automatic update check and download on startup.** `updater.py` gained `resolve_download_url()` and `download_update()`; the About tab runs the check ~500ms after launch when the startup toggle is enabled.

### Changed

- **Combined the About and Updates tabs into one.** Removed `gui/updates_tab.py` and moved its controls into `gui/about_tab.py`; `main_gui.py` no longer creates a separate Updates tab.
- **Updates are staged, not silently applied.** `download_update()` extracts the release into `updates/v<version>/` (an excluded directory) and prompts for a restart instead of overwriting the running process.
- **Reduced updates settings to a single startup toggle.** Removed the manual "Check for Updates" and "Open Releases Page" buttons; only "check on startup" remains.

## [2.1.4] - 2026-07-26

### Changed

- **Made 'archive' the default profile.** Added `DEFAULT_PROFILE = PROFILE_ARCHIVE` in `constants.py`; the GUI Quick Export and the CLI `--profile` default now resolve to archive.
- **Folded expanded-only extensions into archive.** The extra extensions (.rst, .log, .env.example, .sample, .template, .lock) were merged into `ARCHIVE_EXTENSIONS` so no coverage was lost.

### Removed

- **Removed the 'expanded' profile.** Dropped `PROFILE_EXPANDED`, `apply_expanded_preset()`, and the `EXPANDED_*` constants; `VALID_PROFILES` is now `{standard, archive}`.

## [2.1.3] - 2026-07-26

### Changed

- **Centralized profile settings.** The GUI now reads per-profile values from `settings_for_profile()` instead of duplicating them, removing drift between `constants.py` and `gui/builders.py`.
- **Cleaned up the File Index table.** `build_context_markdown()` now builds columns dynamically so 'Lines' and 'SHA256' only appear when their settings are enabled.
- **Hardened scan records and metadata.** Made `FileRecord`, `SkipRecord`, `ScanResult`, and `BuildResult` frozen; added a cached `FileMeta` and skip-reason constants in `scanner.py`.
