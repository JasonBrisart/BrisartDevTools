# Changelog

All notable changes to CanonSync are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-08-09

### Changed
- **Renamed the engine module** `canon_core.py` → `canonsync_core.py` and the
  config `canon.config.json` → `canonsync.config.json` so every file in the
  project shares the `canonsync` prefix. This removes the last trace of the
  old `canon_core` / `sync_core` naming that lingered from the gitignore-only
  predecessor (and left an orphaned `sync_core` `.pyc` in some exports).
- GUI now imports `canonsync_core` and defaults to `canonsync.config.json`.
- `APP_VERSION` bumped to `1.1.0` (single source of truth in
  `canonsync_core.py`; the config mirrors it for display).

### Added
- **Optional backups.** A new `--backup` CLI flag / "Back up files before
  overwriting" GUI checkbox writes a timestamped `<name>.<YYYYMMDD-HHMMSS>.bak`
  beside any file *before* it is overwritten. Applies to updates in both block
  and whole mode. Backups are ignored via the canonical `.gitignore` (`*.bak`).
- **`--version` flag** on the CLI, printing `CanonSync v1.1.0`.
- Backup filenames are surfaced in CLI output and counted in the GUI's
  "Done" dialog.
- Shipped starter `canon/` masters (`gitignore.master`, `editorconfig.master`,
  `gitattributes.master`) and a clearly-marked placeholder `LICENSE`.

### Notes
- The managed-block markers (`BEGIN_MARKER` / `END_MARKER`) are unchanged, so
  existing managed blocks in downstream repos are still recognized — no
  duplicate blocks on upgrade.
- `license` remains `"enabled": false` by default; whole mode is destructive.

## [1.0.0] - 2026-08-09

### Added
- Initial CanonSync release: the generalized successor to the earlier
  gitignore-only sync tool.
- Two sync modes: `block` (managed region, preserves repo-specific content)
  and `whole` (full-file replacement, e.g. LICENSE).
- Pure-standard-library engine (`canon_core.py`) with a CLI, plus a Tkinter
  GUI (`canonsync_gui.py`).
- Repo auto-discovery (one level deep), dry-run preview, confirm-before-apply,
  and idempotent re-runs.
