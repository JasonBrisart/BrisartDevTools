# Architecture

Project Context Helper is organized as one entry point plus four
purpose-built packages.

```
ProjectContextHelper/
├── run.py                  <- the only file you ever run directly
├── docs/                     README.md, ARCHITECTURE.md, CHANGELOG.md
├── core/                    the scan + export engine
│   ├── constants.py           app metadata, profiles, default rules
│   ├── models.py                ScanSettings (+ to/from_jsonable), etc.
│   ├── scanner.py                walks a project folder, decides what's included
│   ├── git_state.py               pure-Python .git reader (Extras-only feature)
│   ├── exporters.py                renders PROJECT_CONTEXT.md / manifest / summary
│   ├── builder.py                   orchestrates one full build (create_context)
│   └── utils.py                      hashing, redaction, timestamps, language hints
├── services/                 stateful support services
│   ├── app_settings.py          persists remaining GUI preference toggles
│   ├── settings_memory.py        always-on last-used-settings save/load (GUI)
│   ├── profile_manager.py         Custom Profiles: named snapshots (Save/Load/Delete)
│   ├── history.py                  records recent exports (About tab list)
│   └── updater.py                   self-update check / download / install
├── cli/                      command-line interface
│   └── cli.py                    argparse wiring, calls core.builder directly
└── gui/                      tkinter desktop interface
    ├── main_gui.py               4-tab notebook shell (Build/Options/Extras/About)
    ├── builders.py                shared GuiState + settings <-> ScanSettings glue
    ├── scroll_frame.py             reusable scrollable-container helper
    ├── build_tab.py                Build tab
    ├── options_tab.py               Options tab
    ├── extras_tab.py                 Extras tab (toggles + Custom Profiles)
    ├── profiles_section.py            Custom Profiles Save/Load/Delete controls
    ├── about_tab.py                    About tab (info, history, updates)
    └── dialogs.py                       shared message-box helpers
```

## Prior layout (before this release)

The version this release replaces (v2.3.5) had a flat layout: every
module (`__init__.py`, `app_settings.py`, `cli.py`, `constants.py`,
`core.py`, `exporters.py`, `history.py`, `models.py`, `run.py`,
`scanner.py`, `updater.py`, `utils.py`) sat directly at the project
root, alongside a `gui/` folder containing exactly six files
(`about_tab.py`, `build_tab.py`, `builders.py`, `dialogs.py`,
`main_gui.py`, `options_tab.py`). `git_state.py`,
`profile_manager.py`, `settings_memory.py`, `scroll_frame.py`,
`extras_tab.py`, and `profiles_section.py` did not exist at all.

## Settings persistence: three distinct mechanisms

1. **Built-in profile defaults** (`core/constants.py`) — `standard`
   and `archive`. Unchanged from the prior version.
2. **Last-used settings, always-on** (`services/settings_memory.py`)
   — GUI-only, no toggle, no way to disable. New in this release; the
   prior version's `make_gui_state()` always started from
   `settings_for_profile(DEFAULT_PROFILE)` with no memory of any
   previous session. The CLI's `--remember-settings` /
   `--use-last-settings` flags (also new) read/write the same file
   but remain explicit opt-in for scripting determinism.
3. **Custom Profiles** (`services/profile_manager.py`) — named,
   multi-slot, always explicit Save/Load/Delete. Entirely new; the
   prior version had no equivalent.

`load_profile()`, `delete_profile()`, and `profile_exists()` in
`profile_manager.py` all strip leading/trailing whitespace from the
requested name before looking it up, matching `save_profile()`'s
existing behavior of always storing a stripped name.

## Why this split

**`core/` never imports from `services/`, `cli/`, or `gui/`.**

**`services/` depends only on `core/`, never on `cli/` or `gui/`.**

**`cli/` and `gui/` are two interchangeable frontends** over the same
`core.builder.create_context()`, differing intentionally only in
whether "last used settings" persist automatically (GUI: yes, always)
or only on request (CLI: opt-in flags only).

## Update checking and version display

`services/updater.py` filters GitHub's full releases list down to
just this tool's releases using `RELEASE_TAG_PREFIX` (releases are
tagged like `project-context-helper-v3.0.0` in the shared
BrisartDevTools monorepo, alongside other independently-versioned
tools) — this filtering logic is unchanged from the prior version.
New in this release: `strip_release_tag_prefix()` removes that prefix
before the version is used in any user-facing message, so what's
shown is a clean version string rather than the full internal tag
name (the prior version displayed the raw tag verbatim in every
update message). This only affects display text — matching a release
by tag prefix and choosing a download asset both still operate on the
untouched, full `tag_name` from the GitHub API.

## GUI: four tabs (was three)

1. **Build** 2. **Options** 3. **Extras** *(new)* 4. **About**

The prior version built exactly three tabs — Build, Options, About —
with no Extras tab, and Options had no Extras or Custom Profiles
content to begin with (it only ever had Export Settings and Included
Output Sections). Both Options and Extras now wrap their content in a
scrollable area (`gui/scroll_frame.py`, also new).

## Core vs. Extras vs. Custom Profiles

1. **Core output toggles** (Options tab). Same two sections
   (Export Settings, Included Output Sections) as the prior version.
2. **Extras (optional)** (Extras tab, top section) — currently just
   `include_git_state`. Entirely new category.
3. **Custom Profiles** (Extras tab, bottom section) — named,
   multi-slot, explicit Save/Load/Delete. Entirely new.

## Shared settings serialization

`core/models.py`'s `ScanSettings.to_jsonable()` (present in the prior
version) and the new `ScanSettings.from_jsonable()` are the single
shared conversion path used by both `services/settings_memory.py` and
`services/profile_manager.py`.

## Import convention

`run.py` inserts the project root onto `sys.path` before importing
anything else -- new in this release, required by the move to
subfolders. The prior version's `run.py` was a single line
(`from cli import main`) with no path bootstrapping needed, since
everything sat flat at the root already.

## App-data file locations

`services/app_settings.py`, `services/settings_memory.py`,
`services/profile_manager.py`, `services/history.py`, and
`services/updater.py` each resolve an `application_dir()` that points
to the project root (the folder containing `run.py`). The prior
version's equivalent modules resolved this as `Path(__file__).parent`
directly (a single `.parent`, appropriate since they lived at the
root); the new versions resolve `.parent.parent` to compensate for
now living one level deeper, inside `services/`.
