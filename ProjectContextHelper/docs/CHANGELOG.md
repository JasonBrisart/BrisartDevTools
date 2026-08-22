# Changelog

All notable changes to Project Context Helper are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.1.0] - 2026-08-22

### Changed — Consolidated All Settings/Profile/History Persistence Into One File
- **All saving and loading logic for App Preferences, Last Used Settings, Custom Profiles, and Build History is now in a single module: `services/storage.py`.** Previously this same functionality was spread across four separate files:
  - `services/app_settings.py` → App Preferences (`app_settings.json`)
  - `services/settings_memory.py` → Last Used Settings (`last_export_settings.json`)
  - `services/profile_manager.py` → Custom Profiles (`custom_profiles.json`)
  - `services/history.py` → Build History (`build_history.json`)
  
  All four of these files have been **removed**. Every function they exposed (`AppPreferences`, `load_preferences()`, `save_preferences()`, `save_last_settings()`, `load_last_settings()`, `clear_last_settings()`, `is_reserved_name()`, `save_profile()`, `load_profile()`, `delete_profile()`, `profile_exists()`, `list_profiles()`, `HistoryEntry`, `append_history_entry()`, `recent_entries()`, `clear_history()`) now lives in `services/storage.py`, organized into four clearly-labeled sections behind one shared `application_dir()` helper.
- **Every other module that reads or writes any of this state now imports exclusively from `services.storage`.** No other file in the codebase performs direct file I/O against any of the four state files. Updated importers:
  - `core/builder.py` — imports `HistoryEntry`, `append_history_entry`
  - `cli/cli.py` — imports the module as `storage` and calls `storage.load_last_settings()`, `storage.save_profile()`, `storage.list_profiles()`, `storage.delete_profile()`, etc.
  - `gui/builders.py` — imports `AppPreferences`, `load_preferences`, `save_preferences`, `load_last_settings`, `save_last_settings`
  - `gui/profiles_section.py` — imports the module as `storage` and calls `storage.save_profile()`, `storage.load_profile()`, `storage.delete_profile()`, `storage.list_profiles()`, `storage.is_reserved_name()`
  - `gui/about_tab.py` — imports `HistoryEntry`, `application_dir`, `clear_history`, `recent_entries`
- **`services/updater.py` now also imports `application_dir()` from `services.storage`** instead of maintaining its own separate copy of the same resolution logic. Updater-specific concerns (checking for releases, staging downloads, backing up and swapping application files) remain in `updater.py`, since those are a genuinely different responsibility (updating the application itself, not persisting user settings) — but the one piece of logic the two modules had been duplicating (where does this app's data live) is now shared from a single source.
- **Root motivation:** four modules each independently re-implementing the same `application_dir()` frozen-vs-source resolution helper is exactly the kind of duplication that lets small inconsistencies creep in silently — a fix or behavior change applied to one copy has no guarantee of reaching the other three. Consolidating into one file removes that entire class of risk going forward, and makes "where does saving happen" a single, findable answer instead of a four-way guessing game.

### Notes
- **This is a pure internal refactor with zero behavior change.** Every file format, every JSON key, every CLI flag, every GUI control, and every function's signature and return value are identical to before. `custom_profiles.json`, `last_export_settings.json`, `app_settings.json`, and `build_history.json` are read and written in the exact same shape as previously; a file saved by the pre-refactor version loads correctly under this version and vice versa.
- The whitespace-stripping fix for Custom Profile names (`v3.0.0`) carried over unchanged into the consolidated `save_profile()` / `load_profile()` / `delete_profile()` / `profile_exists()` in `storage.py` — re-verified as part of this refactor, not silently dropped.
- Verified end-to-end after the consolidation: a full CLI build with `--git-state` completed correctly (confirming `core/builder.py`'s new import path for `HistoryEntry`/`append_history_entry` works); the complete Custom Profiles lifecycle (save → list → load-with-trailing-whitespace → delete → confirm gone) was re-run against the consolidated module with identical results to before; and a full two-launch GUI cycle confirmed both the always-on Last Used Settings memory and the App Preferences autosave (`open_after_build`, etc.) persist correctly across a simulated restart, all now flowing through the single `services/storage.py` module.
- Searched the entire codebase after the refactor for any remaining reference to the four removed module names (`app_settings`, `settings_memory`, `profile_manager`, a standalone `services.history` import) — none found outside of comments/docstrings explaining the change and the filename constants themselves (which still live in `core/constants.py`, unchanged).

---

## [3.0.0] - 2026-08-22

This release consolidated a full architecture overhaul plus every
feature and fix built on top of it in the same development cycle: a
complete project restructure, opt-in Git State detection, an
Extras/Custom Profiles system, a GUI tab split with scroll support,
always-on settings memory, and two bug fixes. It replaced the prior
flat-file-layout version (v2.3.5) in one step.

### Added — Project Restructure (Architecture Foundation)
- Reorganized the entire codebase from a flat file layout into purpose-built subfolders (`core/`, `services/`, `cli/`, `gui/`, `docs/`), with a single entry point (`run.py`).
- Every internal import updated to fully package-qualified paths.
- Removed the old root-level `__init__.py`.

### Fixed — Project Restructure
- Fixed an `application_dir()` regression introduced by the move itself, so app-data files continued landing next to `run.py` rather than nested inside `services/`.

### Added — Git State Detection (Extras, opt-in)
- New `core/git_state.py` module: reads a project's `.git` directory directly (HEAD, refs, loose commit/tree objects), pure Python, no external `git` binary invoked.
- New "Git State" section in `PROJECT_CONTEXT.md`, `PROJECT_MANIFEST.json`, and `PROJECT_SUMMARY.txt`.
- Recent Exports history records branch + short commit. Build Complete dialog and CLI output show a one-line git summary.
- CLI `--git-state` / `--no-git-state` / `--git-state-commit-limit` flags.
- Off by default in both `standard` and `archive` profiles, including archive/maximum-preservation mode — lives in the Extras (Optional) category, never enabled by a profile preset.

### Added — Extras (Optional) Category
- New "Extras (Optional)" section (later split onto its own tab): a dedicated category for niche add-ons never enabled by a profile preset.

### Added — Custom Profiles
- Named, user-managed settings snapshots with explicit Save / Load / Delete actions, distinct from both built-in presets and the automatic Last Used Settings.
- CLI: `--save-profile NAME`, `--load-profile NAME`, `--delete-profile NAME`, `--list-profiles`.
- `ScanSettings.from_jsonable()` classmethod added, the counterpart to the existing `to_jsonable()`.
- `apply_settings_to_state()` fixed to also set the Output Folder field (a pre-existing gap).
- New `apply_custom_profile_to_state()` helper, ensuring loaded profile values correctly win over base-profile defaults.

### Changed — GUI Restructure (3 tabs → 4 tabs; Options split into Options + Extras)
- Options tab no longer requires maximizing the window to see everything — split into "Options" and "Extras" tabs.
- Both tabs made scrollable via new `gui/scroll_frame.py`.

### Changed — Settings Are Always Remembered (GUI)
- "Remember Last Used Settings" made always-on, unconditional GUI behavior — no toggle, no way to disable.
- The profile dropdown became the explicit "reset to defaults" path.
- Scoped to the GUI only, by design: the CLI's `--remember-settings` / `--use-last-settings` flags remain separate and explicit opt-in.

### Fixed — Bug Fixes
- Update messages displayed the full internal release tag instead of a clean version number — fixed with `strip_release_tag_prefix()`.
- Custom Profile names with leading/trailing whitespace could silently fail to be found via the CLI's `--load-profile` flag — fixed by stripping names before lookup in all relevant functions.

### Notes
- This release established the folder architecture as the permanent foundation the project builds on going forward.

---
## [2.3.5] - 2026-08-17
### Fixed
- A source file could be silently skipped if it matched a compound extension (like `.env.example`) by name only, not by suffix. `is_configured_source_file()` now also matches by filename ending for compound extensions.
---
## [2.3.4] - 2026-08-11
### Fixed
- The updater could fall back to downloading the entire BrisartDevTools monorepo instead of just this tool. `resolve_asset()` no longer falls back to a repository-wide source archive; reports `asset_kind == "none"` instead.
---
## [2.3.3] - 2026-08-11
### Fixed
- A source file could be silently and incorrectly skipped if its filename matched an excluded directory name (e.g. a file literally named `build`). `exclusion_reason()` now only checks directory-name exclusions against actual directory components.
---
## [2.3.2] - 2026-08-11
### Fixed
- App-level preference toggles did not persist across restarts. Added `app_settings.py` with write-through autosave (later consolidated into `services/storage.py` in v3.1.0; see above).
---
## [2.2.1] - 2026-08-11
### Fixed
- Update check could select another tool's release in the BrisartDevTools monorepo. Update checks now filter the full releases list by tag prefix.
---
## [2.2.0] - 2026-08-11
### Added
- Real in-place auto-updater, with every in-place update backed up first, and a CLI `--install-updates` flag.
---
## [2.1.5] - 2026-07-26
### Added
- Automatic update check and download on startup. Combined the About and Updates tabs into one.
---
## [2.1.4] - 2026-07-26
### Changed
- Made 'archive' the default profile. Folded expanded-only extensions into archive; removed the 'expanded' profile.
---
## [2.1.3] - 2026-07-26
### Changed
- Centralized profile settings; cleaned up the File Index table; hardened scan records and metadata.
