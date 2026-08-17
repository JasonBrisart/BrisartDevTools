# Changelog

All notable changes to Project Context Helper are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.5] - 2026-08-17

### Fixed
- **A source file could be silently skipped if it matched a compound extension by name only, not by suffix.** `is_configured_source_file()` in `scanner.py` matched files against `settings.include_extensions` using `Path.suffix` (the file's last dot-segment) plus an exact `name_lower` match. This works for ordinary single-dot extensions, but `Path.suffix` only ever returns the *last* dot-segment of a filename — so for a genuinely compound profile extension like `.env.example` (present in the archive profile by default), only a file literally named `.env.example` (nothing before the leading dot) was ever matched. A file named `config.env.example` or `backend/api.env.example` — an extremely common real-world naming pattern for example-env files — resolved to a suffix of `.example` (not in the list) and a `name_lower` of `config.env.example` (also not in the list), and was silently dropped from every export.
- **This went undetected by the archive-mode source completeness check**, for the same reason as the v2.3.3 fix: the resulting skip reason, `extension_not_included`, is an intentional-exclusion reason and was never part of `SOURCE_COMPLETENESS_FAILURE_REASONS`, so a build hitting this exact naming pattern still reported `Status: PASS` in `PROJECT_MANIFEST.json` while quietly missing a real, eligible source file.

### Changed
- **`is_configured_source_file()` now also matches by filename ending, for compound extensions only.** After the existing suffix and exact-name checks, it additionally matches when a filename ends with any configured extension that itself contains more than one dot (currently just `.env.example`). Ordinary single-dot extensions (`.py`, `.md`, `.sample`, `.template`, `.lock`, etc.) are untouched and continue to be matched exactly as before — this only changes behavior for genuinely compound extension entries.

### Notes
- Scope is narrow by design: only extension entries containing more than one dot are eligible for the new ending-match check, so there is no risk of a single-dot extension like `.m` or `.r` unexpectedly matching an unrelated file.
- No manifest, settings, or export format changes. No migration step required.
- Verified with a fixture project containing `.env.example` at the root and `backend/config.env.example` nested one level down, using the real `collect_included_files()` scan path: before the fix, only the root `.env.example` was included and `backend/config.env.example` was skipped as `extension_not_included` with the archive build still reporting `PASS`; after the fix, both files are included and correctly hashed/line-counted like any other source file.

---

## [2.3.4] - 2026-08-11

### Fixed

- **The updater could fall back to downloading the entire BrisartDevTools monorepo instead of just this tool.** `resolve_asset()` in `updater.py` previously fell back to `payload.get("zipball_url")` whenever no matching `.exe` or `.zip` release asset was found on a release. GitHub's `zipball_url` (and `tarball_url`) always packages the full repository source at that commit — every tool in the monorepo, not just Project Context Helper — so a release published without the expected asset attached would cause the updater to silently download, and (if auto-install was enabled) extract the whole repository over the application's own files.

### Changed

- **`resolve_asset()` no longer falls back to a repository-wide source archive.** It now only returns a `.exe` asset (when running as a frozen executable) or a `.zip` asset (when running from source). If neither is attached to the matched release, it returns a new `asset_kind` of `"none"` with an empty download URL, so nothing is ever downloaded.
- **`check_for_updates()` reports `asset_kind == "none"` explicitly.** `update_available` can still be `True` in this case (so the UI can tell the user a newer release exists), but `download_url` is empty and the message states plainly that no compatible asset was found for the current run mode.
- **CLI and GUI update flows both stop cleanly on `asset_kind == "none"`.** `run_update_check()` in `cli.py` prints the release page and returns without downloading. `perform_auto_update()` in `gui/about_tab.py` shows an info dialog and returns without downloading.

### Notes

- A correctly packaged release (with a `.zip` or `.exe` asset attached, per the project's normal release process) is unaffected by this change and updates exactly as before.
- No manifest, settings, or export format changes. No migration step required.
- Verified with a simulated release payload containing no `.exe` or `.zip` assets: before the fix, `resolve_asset()` returned the repository `zipball_url`; after the fix, it returns `("", "none", "")` and both the CLI and GUI update paths stop without downloading anything.

---

## [2.3.3] - 2026-08-11

### Fixed

- **A source file could be silently and incorrectly skipped if its filename matched an excluded directory name.** `exclusion_reason()` in `scanner.py` checked every component of a file's relative path against `exclude_dirs`, including the file's own filename. A file literally named `build`, `dist`, `env`, `venv`, or `updates` (all default excluded directory names, per `DEFAULT_EXCLUDE_DIRS` in `constants.py`) anywhere in the project — most commonly an extensionless build/config script at the project root — was reported as `excluded_directory:<name>` and dropped from the export, even though it was a file, not a directory.
- **This went undetected by the archive-mode source completeness check.** `excluded_directory:*` is an intentional-exclusion reason and was never part of `SOURCE_COMPLETENESS_FAILURE_REASONS`, so a build hitting this bug still reported `Status: PASS` in `PROJECT_MANIFEST.json` and claimed every eligible source file was captured, while actually missing a real file with no warning anywhere in the output.

### Changed

- `exclusion_reason()` now only checks directory-name exclusions against a path's actual directory components. When the candidate path is a file, its own final path segment (the filename) is excluded from that check; when it is a directory, the full path is checked as before. File-name and suffix exclusion checks (`exclude_files`, `exclude_suffixes`) are unaffected.

### Notes

- Genuine excluded directories (e.g. an actual `build/` or `dist/` folder and everything inside it) continue to be excluded exactly as before — this fix only stops same-named *files* from being misclassified as directories.
- No manifest, settings, or export format changes. No migration step required.
- Verified by adding a zero-byte file named `build` (no extension) at a project root that also contains a genuine `dist/` directory: before the fix, the file was skipped with `excluded_directory:build` and the archive-mode build still reported `PASS`; after the fix, the file is scanned normally against the configured extension list, while the real `dist/` directory is still fully excluded.

---

## [2.3.2] - 2026-08-11

### Fixed

- **App-level preference toggles did not persist across restarts.** "Automatically check for and download updates on startup," "Automatically install downloaded updates," and "Open export folder after build" all reset to unchecked every time the application was reopened, including the compiled `.exe`, regardless of what the user had previously selected. Root cause: `make_gui_state()` hardcoded all three toggles to `False` on every call — there was no save or load step for them at all.

### Added

- **`app_settings.py`.** New module that persists the three app-level preference toggles to `app_settings.json`, written next to the application itself (using the same frozen-aware `application_dir()` pattern as `updater.py` and `history.py`, so it resolves correctly whether running from source or as a compiled `.exe`).
- **Write-through autosave for preference toggles.** `gui/builders.py` gained `wire_preference_autosave()`, which attaches a `trace_add("write", ...)` callback to each of the three toggles so a change is written to disk immediately when the checkbox is clicked — no explicit "save" action or clean shutdown required.
- **`APP_SETTINGS_FILENAME` constant.** Added to `constants.py` and included in `DEFAULT_EXCLUDE_FILES`, so `app_settings.json` is never accidentally swept into a project export.

### Notes

- Per-export scan settings (profile, extensions, size limits, etc.) are unrelated to this fix and continue to reset to the selected profile's defaults on every launch, as before. Only the three app-level preference toggles are persisted.
- Verified with a full save/reload roundtrip test: fresh install defaults to unchecked, toggling a checkbox writes to `app_settings.json` immediately, and a simulated restart correctly restores the prior checkbox states — including confirming `app_settings.py` resolves to the identical folder as `updater.py`/`history.py` when running as a compiled exe.

---

## [2.2.1] - 2026-08-11

### Fixed

- **Update check could select another tool's release in the BrisartDevTools monorepo.** `check_for_updates()` previously queried GitHub's `/releases/latest` endpoint, which returns the newest release for the entire `BrisartDevTools` repository rather than the newest Project Context Helper release specifically. Since the repo also contains independently versioned tools (CanonSync, AutoExeBuilder, ReadmeBuilder, ReleaseNoteBuilder), publishing a release for any other tool after the latest Project Context Helper release would cause the updater to detect, download, and apply that other tool's release instead.
- **Update checks now filter the full releases list by tag prefix.** `constants.py` replaces `UPDATE_CHECK_URL` with `RELEASES_LIST_URL` (the full `/releases` list) and a new `RELEASE_TAG_PREFIX = "project-context-helper-v"`. `updater.py` gained `find_latest_release_payload()`, which walks the list and returns the first release whose tag actually starts with that prefix, ignoring newer releases belonging to other tools in the repo.

### Notes

- If no release matching the tag prefix is found (e.g. the prefix convention changes, or no Project Context Helper release exists yet), `check_for_updates()` now reports this explicitly instead of silently falling back to an unrelated release.
- Verified with a simulated monorepo releases list (`canonsync-v1.2.0` listed as newest, `project-context-helper-v2.2.0` and `-v2.1.5` behind it): confirmed the old `/releases/latest`-style logic would have selected the CanonSync release, and confirmed the fixed filtering logic correctly selects the matching Project Context Helper release instead.

---

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

---

## [2.1.5] - 2026-07-26

### Added

- **Automatic update check and download on startup.** `updater.py` gained `resolve_download_url()` and `download_update()`; the About tab runs the check ~500ms after launch when the startup toggle is enabled.

### Changed

- **Combined the About and Updates tabs into one.** Removed `gui/updates_tab.py` and moved its controls into `gui/about_tab.py`; `main_gui.py` no longer creates a separate Updates tab.
- **Updates are staged, not silently applied.** `download_update()` extracts the release into `updates/v<version>/` (an excluded directory) and prompts for a restart instead of overwriting the running process.
- **Reduced updates settings to a single startup toggle.** Removed the manual "Check for Updates" and "Open Releases Page" buttons; only "check on startup" remains.

---

## [2.1.4] - 2026-07-26

### Changed

- **Made 'archive' the default profile.** Added `DEFAULT_PROFILE = PROFILE_ARCHIVE` in `constants.py`; the GUI Quick Export and the CLI `--profile` default now resolve to archive.
- **Folded expanded-only extensions into archive.** The extra extensions (.rst, .log, .env.example, .sample, .template, .lock) were merged into `ARCHIVE_EXTENSIONS` so no coverage was lost.

### Removed

- **Removed the 'expanded' profile.** Dropped `PROFILE_EXPANDED`, `apply_expanded_preset()`, and the `EXPANDED_*` constants; `VALID_PROFILES` is now `{standard, archive}`.

---

## [2.1.3] - 2026-07-26

### Changed

- **Centralized profile settings.** The GUI now reads per-profile values from `settings_for_profile()` instead of duplicating them, removing drift between `constants.py` and `gui/builders.py`.
- **Cleaned up the File Index table.** `build_context_markdown()` now builds columns dynamically so 'Lines' and 'SHA256' only appear when their settings are enabled.
- **Hardened scan records and metadata.** Made `FileRecord`, `SkipRecord`, `ScanResult`, and `BuildResult` frozen; added a cached `FileMeta` and skip-reason constants in `scanner.py`.
