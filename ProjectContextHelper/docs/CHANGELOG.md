# Changelog

All notable changes to Project Context Helper are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.0.0] - 2026-08-22

This release consolidates a full architecture overhaul plus every
feature and fix built on top of it in the same development cycle: a
complete project restructure, opt-in Git State detection, an
Extras/Custom Profiles system, a GUI tab split with scroll support,
always-on settings memory, and two bug fixes. Nothing in this release
was shipped as a separate intermediate version — it replaces v2.3.5
(the version this changelog previously ended at) in one step. Every
"before" detail below was verified directly against the actual
v2.3.5 source rather than from memory.

### Added — Project Restructure (Architecture Foundation)
- **Reorganized the entire codebase from a flat file layout into purpose-built subfolders, with a single entry point.** The v2.3.5 layout had every module — `__init__.py`, `app_settings.py`, `cli.py`, `constants.py`, `core.py`, `exporters.py`, `history.py`, `models.py`, `run.py`, `scanner.py`, `updater.py`, `utils.py` — sitting directly at the project root, alongside a `gui/` folder containing exactly six files (`about_tab.py`, `build_tab.py`, `builders.py`, `dialogs.py`, `main_gui.py`, `options_tab.py`). The new layout is:
  - `run.py` — the only file at the project root; the single, obvious way to start the program (`python run.py`). Previously this file contained only `from cli import main`; it now also inserts the project root onto `sys.path` before importing, since nothing else can resolve its package-qualified imports otherwise.
  - `core/` — the scan + export engine: `constants.py`, `models.py`, `scanner.py`, `exporters.py`, `utils.py` (moved as-is), plus `builder.py` (renamed from the old root-level `core.py`, to avoid a confusing `core/core.py`), plus the entirely new `git_state.py`.
  - `services/` — stateful support services: `app_settings.py`, `history.py`, `updater.py` (moved as-is), plus the entirely new `settings_memory.py` and `profile_manager.py`.
  - `cli/` — the command-line interface (`cli.py`, moved as-is).
  - `gui/` — the desktop interface: the same six files as before (`main_gui.py`, `builders.py`, `build_tab.py`, `options_tab.py`, `about_tab.py`, `dialogs.py`), plus three entirely new files (`scroll_frame.py`, `extras_tab.py`, `profiles_section.py`).
  - `docs/` — `README.md` and `ARCHITECTURE.md` (both new), and `CHANGELOG.md` (moved from the project root, content preserved in full below).
- **Every internal import was updated to fully package-qualified paths** (e.g. `from core.constants import ...`, `from services.history import ...`) so every module resolves correctly regardless of which directory the process is launched from.
- Removed the old root-level `__init__.py`, since the project root is no longer meant to be imported as a package from outside — it's a standalone application you `cd` into and run via `run.py`.

### Fixed — Project Restructure
- **Fixed an `application_dir()` regression introduced by the move itself.** In v2.3.5, `app_settings.py`, `history.py`, and `updater.py` each resolved their own data-file folder as `Path(__file__).resolve().parent` — a single `.parent`, correct because those modules lived directly at the project root. Simply moving these files (plus the two new services modules) into `services/` without changing that logic would have caused all of them to nest their data files inside `services/` instead of next to `run.py`. All five `services/*.py` modules now resolve `.parent.parent` in source mode to compensate for living one level deeper; frozen-executable behavior (resolving to the `.exe`'s own folder) is unaffected either way.

### Added — Git State Detection (Extras, opt-in)
- **New `core/git_state.py` module.** v2.3.5 had no concept of git anywhere — no git-related code in `core.py`, `models.py`, `exporters.py`, or `cli.py`, and `BuildResult`/`HistoryEntry` had no git fields at all. This release adds a module that reads a project's `.git` directory directly (HEAD, refs, loose commit/tree objects) to report the current branch, HEAD commit, whether the working tree is dirty or clean versus HEAD, modified/deleted/untracked file lists, and the last few commit summaries — all pure Python, with zero external dependencies and **no subprocess call into a `git` binary**. Object hashing and decompression use only `hashlib` and `zlib` from the standard library.
- **New "Git State" section in `PROJECT_CONTEXT.md`**, placed directly after Export Summary (v2.3.5's `PROJECT_CONTEXT.md` went straight from Export Summary to Source Completeness Check). Also added to `PROJECT_MANIFEST.json` (`git_state` key) and `PROJECT_SUMMARY.txt`.
- **Recent Exports history records branch + short commit** for every build. v2.3.5's `HistoryEntry` dataclass had exactly 7 fields (`created`, `root`, `profile`, `export_dir`, `included_count`, `skipped_count`, `total_included_bytes`); this release adds `git_branch` and `git_commit_short`, shown in a new "Git" column in the About tab's history table (v2.3.5's `history_tree` had exactly 5 columns: `created`, `profile`, `included`, `skipped`, `root` — no `git` column).
- **Build Complete dialog and CLI output show a one-line git summary** (`branch @ commit (clean/dirty/unverified)`) whenever a repository was detected. v2.3.5's `show_build_complete()` and CLI output had no equivalent line at all.
- **CLI `--git-state` / `--no-git-state` flags**, and `--git-state-commit-limit` to control how many recent commits are listed. None of these three flags existed in v2.3.5's `cli.py`.
- `ScanSettings` gained `include_git_state` (default `False`) and `git_state_commit_limit` (default `5`) — two entirely new fields; v2.3.5's `ScanSettings` had 19 fields total and stopped at `require_complete_source`. `BuildResult` gained `git_branch`, `git_commit_short`, and `git_is_dirty`.
- `core.builder.create_context()` (formerly `core.create_context()`) computes `GitState` **exactly once per build** and threads the same instance into the markdown, manifest, and summary exporters, rather than letting each exporter recompute it independently — the dirty-tree check walks the entire working tree, so recomputing it three times per build would have been wasteful and could theoretically disagree with itself if files changed mid-build.
- The working-tree dirty/untracked scan reuses the build's own `exclude_dirs` / `exclude_files` sets (the same ones already applied to the project scan), so noise like `__pycache__`, virtual environments, and this tool's own `PROJECT_CONTEXT_EXPORTS/` folder is never reported as "untracked."
- **Packed repositories (after `git gc`, or a shallow/packed clone) are handled gracefully**: when a needed object lives inside a `.pack` file rather than as a loose object, detection stops at that point and records a `warnings` entry instead of guessing or crashing. `is_dirty` becomes `None` ("could not be verified") rather than a false `False` in that case.
- Submodules (gitlinks) are recognized and excluded from the dirty-tree comparison rather than being treated as ordinary files.
- **Include Git State is opt-in and off by default in both `standard` and `archive` profiles**, including archive/maximum-preservation mode — "maximum preservation" governs the core output files (hashes, line counts, full contents, source-completeness enforcement); it intentionally does not imply every niche extra is auto-enabled. It lives in the Extras (Optional) category (see below), never enabled by a profile preset.
- Verified against real git repositories in every relevant state: clean, modified/untracked/deleted files, detached HEAD, branch resolved via `packed-refs` instead of a loose ref, and a fully packed repository (post `git gc --aggressive`) — output was cross-checked directly against `git status --short` and `git log --oneline`.

### Added — Extras (Optional) Category
- **New "Extras (Optional)" section**, later split onto its own "Extras" tab (see GUI Restructure below): a dedicated category for niche, specific-use-case add-ons that are never enabled by a profile preset and never change any of the core export sections (Export Summary, Source Completeness, Folder Tree, File Index, File Contents) unless explicitly turned on. v2.3.5's Options tab had no such category — it only ever had "Export Settings" and "Included Output Sections."

### Added — Custom Profiles
- **Named, user-managed settings snapshots** with explicit Save / Load / Delete actions, distinct from both the two built-in presets (`standard`, `archive`) and from the automatic, unnamed, always-on "last used settings" behavior (see below). None of this existed in v2.3.5: no `custom_profiles.json`, no `--save-profile`/`--load-profile`/`--delete-profile`/`--list-profiles` CLI flags, and no `custom_profile_var` anywhere in `gui/builders.py`'s `GuiState` (whose full field list in v2.3.5 was: `selected_folder`, `profile_var`, `output_dir_var`, `max_file_mb_var`, `max_total_mb_var`, `skipped_limit_var`, `include_zip_var`, `redact_var`, `include_hashes_var`, `include_line_counts_var`, `include_tree_var`, `include_index_var`, `include_contents_var`, `include_skipped_details_var`, `timestamped_folder_var`, `open_after_build_var`, `check_updates_startup_var`, `auto_install_var`, `status_text`, `last_export_dir` — 20 fields, none related to git or profiles). New service module `services/profile_manager.py`, storing every saved profile (keyed by name) in `custom_profiles.json` next to `run.py`.
- **New "Custom Profiles" section** (`gui/profiles_section.py`, a new file): a name field (type a new name, or pick an existing one from the dropdown) plus **Save Current As**, **Load Selected**, **Delete Selected**, and **Refresh List** buttons. "Save Current As" saves exactly what an immediate build would use (via the same `build_settings_from_state()` already used by the Build tab), so a saved profile can never drift from what was actually on screen when it was saved.
- **CLI equivalents:** `--save-profile NAME` (save the settings used in this run), `--load-profile NAME` (load a named profile as the base before other flags override it), `--delete-profile NAME`, `--list-profiles`.
- **`ScanSettings.from_jsonable()` classmethod** (`core/models.py`), the counterpart to the existing `to_jsonable()` (which v2.3.5 already had). Extra/unknown keys in a loaded dict are silently ignored rather than raising, so a settings file saved by a future version can still be loaded by an older one. This is the single shared reconstruction path used by both `services/settings_memory.py` and `services/profile_manager.py`, so the two features can never silently drift apart in how they interpret a saved settings dict.
- **`apply_settings_to_state()` (`gui/builders.py`) now also sets the Output Folder field.** v2.3.5's version of this same function set every other field (max file/total MB, skipped-details limit, all output-section checkboxes) but never touched `output_dir_var` — a pre-existing gap that went unnoticed until Custom Profiles needed a truly complete round-trip of every GUI-exposed field, including a profile that *does* use a custom output folder.
- **New `apply_custom_profile_to_state()` helper (`gui/builders.py`).** Loading a Custom Profile sets the profile dropdown to that profile's base ("standard" or "archive") first — which re-triggers the existing profile-change logic and resets every field to that base profile's plain defaults — then immediately re-applies the actual loaded settings on top, so the real saved values always win over the just-applied defaults.
- Custom Profiles capture every setting that has a corresponding GUI control (profile, output folder, size limits, and every Included Output Sections / Extras toggle). `include_extensions` / `exclude_dirs` / `exclude_files` / `exclude_suffixes` are still driven entirely by the selected base profile, exactly as in v2.3.5 — there is no GUI control for editing them directly, so this isn't a new limitation.
- Reserved-name protection is case-insensitive: a Custom Profile cannot be saved as `"Standard"`, `"ARCHIVE"`, etc., not just the exact lowercase built-in names.
- Verified end-to-end: CLI `--save-profile` / `--list-profiles` / `--load-profile` / `--delete-profile` were run against a real project in sequence (save → list → load with a different `--profile` base to confirm the override wins → delete → confirm the name is gone → delete again to confirm the "not found" path doesn't error); the GUI-side save/load round trip was tested directly against the real `gui.builders` functions with a stateful tkinter stub, confirming a value that a base profile's defaults would normally reset (e.g. `include_hashes` under the `standard` profile) is correctly restored to its saved value after `apply_custom_profile_to_state()` runs.

### Changed — GUI Restructure (3 tabs → 4 tabs; Options split into Options + Extras)
- **The Options tab no longer requires maximizing the window to see everything.** By the point Extras and Custom Profiles had both been added to it, it had grown to four stacked sections and no longer reliably fit inside the default 860x760 window (v2.3.5's Options tab, with only its original two sections, fit comfortably at that same window size).
- **Split into two tabs: "Options" and "Extras."** Options now holds only Export Settings and Included Output Sections — identical in content to v2.3.5's Options tab. The new **Extras** tab holds the Extras (Optional) toggles and the Custom Profiles section. `gui/main_gui.py` now builds a 4-tab notebook (Build / Options / Extras / About) — v2.3.5 built exactly 3 (`notebook.add(build_tab, ...)`, `notebook.add(options_tab, ...)`, `notebook.add(about_tab, ...)`, in that order, with nothing in between).
- **Both the Options and Extras tabs are scrollable.** New `gui/scroll_frame.py` provides `create_scrollable_area(parent)`, a small reusable helper (Canvas + Scrollbar + an inner content `tk.Frame`) that section-building code treats exactly like any other frame. v2.3.5's `options_tab.py` packed its `LabelFrame` sections directly into the tab's plain `tk.Frame`, with no scrolling mechanism of any kind. Scrolling works via the scrollbar or the mouse wheel; the wheel binding is scoped to only be active while the cursor is over that specific tab's canvas (bound on `<Enter>`, unbound on `<Leave>`), so it can't interfere with, e.g., the Recent Exports Treeview's own scrolling on the About tab.
- This split reinforces the three-tier design documented in `docs/ARCHITECTURE.md` (Core output toggles vs. Extras vs. Custom Profiles) with an actual tab boundary, rather than just a visual section divider within one crowded tab.
- Verified: `create_scrollable_area()` was exercised directly (canvas resize correctly propagates to the inner content's width; the mouse-wheel handler computes the correct scroll direction and amount from a wheel event's `delta`; the binding is correctly registered on `<Enter>` and removed on `<Leave>`); Custom Profiles (buttons on the Extras tab) was confirmed to still correctly read and write toggles that live on the Options tab, since everything shares one `GuiState` object regardless of which tab renders which widget; and the full CLI build pipeline was re-run end-to-end to confirm nothing else regressed.

### Changed — Settings Are Always Remembered (GUI)
- **"Remember Last Used Settings" is not a toggle — it is always-on, unconditional GUI behavior.** v2.3.5 had no concept of this at all: `make_gui_state()` there always called `settings_for_profile(DEFAULT_PROFILE)` directly with zero memory of any prior session, every single launch. This release adds `services/settings_memory.py`: every successful GUI build silently saves the settings used (`gui/builders.py: run_project_build()` unconditionally calls `save_last_settings()`), and every GUI launch silently loads them back in place of the selected profile's plain defaults (`make_gui_state()` unconditionally calls `load_last_settings()`). There is no checkbox for this anywhere in the GUI, and no way to disable it.
- **The profile dropdown is the explicit "reset to defaults" path.** Since settings are always remembered with no opt-out, manually picking `standard` or `archive` from the Build tab's profile dropdown (`apply_profile_defaults()`, unchanged from v2.3.5) is the way to discard whatever was auto-loaded and start from a known baseline.
- **Scoped to the GUI only, by design.** The CLI's `--remember-settings` (save) and `--use-last-settings` (load) flags — both new, neither existed in v2.3.5's `cli.py` — are separate and remain explicit opt-in: CLI invocations are typically scripted or automated, and silently loading hidden state left over from a previous run would break reproducibility for anyone relying on deterministic behavior. Both interfaces read and write the exact same `last_export_settings.json` file, so a value saved by one can be picked up by the other.
- No change to any core export file format (`PROJECT_CONTEXT.md`, `PROJECT_MANIFEST.json`, `PROJECT_SUMMARY.txt`), no change to Custom Profiles behavior, and no change to any other CLI flag.
- Verified end-to-end: confirmed the GUI's internal state has no "remember" toggle field at all; ran a full first-launch → customize-and-build → simulated-restart cycle confirming settings are saved and reloaded with zero toggle interaction; confirmed picking a profile from the dropdown still correctly discards auto-loaded values in favor of that profile's plain defaults; confirmed the CLI's opt-in flags still work exactly as intended, while a plain CLI build with neither flag correctly does **not** touch `last_export_settings.json` at all.

### Fixed — Bug Fixes
- **Update messages displayed the full internal release tag instead of a clean version number.** v2.3.5's `check_for_updates()` used `payload.get("tag_name") or payload.get("name") or APP_VERSION` directly as `UpdateInfo.latest_version`, with no stripping of any kind — so every user-facing message (CLI stdout, the GUI's Updates status text, and the "Update Available"/"Update Downloaded"/"Update Installed" dialogs) would have shown the ugly, full tag string (e.g. `"project-context-helper-v9.9.9"`) instead of just `"9.9.9"`. This did not affect the actual newer-vs-older version comparison (`is_newer_version()`/`normalize_version()` already stripped all non-digit/non-dot characters, and the tag prefix itself contains no digits), so no update was ever wrongly skipped or wrongly applied in v2.3.5 — this was purely a display bug that this release fixes. New `strip_release_tag_prefix()` function removes the known `RELEASE_TAG_PREFIX` before the version is used in any message; `find_latest_release_payload()` and `resolve_asset()` are unaffected and continue to match against the full, untouched `tag_name`, exactly as in v2.3.5.
- **Custom Profile names with leading/trailing whitespace could silently fail to be found**, even though the "same" profile (from a user's perspective) clearly existed. Since Custom Profiles are new in this release, this was never an issue an external user could have hit in v2.3.5 — it was introduced and fixed within this same development cycle before shipping. `services/profile_manager.py`'s `save_profile()` always stripped the name before storing it as a dict key, but `load_profile()`, `delete_profile()`, and `profile_exists()` initially compared the raw, un-stripped input directly against those already-stripped keys. The GUI's `gui/profiles_section.py` always stripped names itself before calling into `profile_manager`, which is why this went unnoticed there — but `cli/cli.py`'s `--load-profile` flag passed `args.load_profile` straight through unstripped, so a profile saved as `"MyProfile"` could fail to load via `--load-profile "MyProfile "` (a single trailing space, e.g. from copy/paste or imprecise shell quoting), printing a "not found" warning and silently falling back to the settings that would otherwise apply instead. All three functions now strip the name before lookup, matching `save_profile()`'s behavior.
- Both fixes are narrowly scoped and backward compatible: no change to any saved file's format, no change to any CLI flag's name or meaning, and no change to `ScanSettings` or any export file.
- Verified directly: `strip_release_tag_prefix()` was tested against a simulated GitHub releases payload confirming the before/after message difference (`"project-context-helper-v9.9.9"` → `"9.9.9"`), and `is_newer_version()` was re-confirmed to still correctly compare cleaned version strings. For the profile-name fix, a profile was saved under a clean name and then successfully looked up, checked for existence, and deleted using names with added leading and/or trailing whitespace — and the exact real-world CLI scenario (`--load-profile "Name "` with a trailing space) was reproduced end-to-end and confirmed fixed.

### Notes
- This release establishes the folder architecture (`core/`, `services/`, `cli/`, `gui/`, `docs/`) as the permanent foundation the project builds on going forward.
- Verified end-to-end after the full set of changes: a real build was run from a completely different working directory than the project root (confirming `run.py`'s `sys.path` bootstrap resolves every package-qualified import correctly), `build_history.json` / `app_settings.json` / `last_export_settings.json` / `custom_profiles.json` all land next to `run.py` rather than nested inside `services/`, and the full CLI and GUI code paths were exercised together under the final `v3.0.0` version label with no regressions found.

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