# Project Context Helper

Project Context Helper packages a project directory into a structured context bundle suitable for documentation, review, archival, collaboration, and AI-assisted development workflows.

## Features

- Recursive project scanning
- Folder tree generation
- Source file aggregation
- JSON manifest generation
- ZIP snapshot creation
- GUI and CLI support
- No third-party dependencies

## Output

```text
PROJECT_CONTEXT.md
PROJECT_MANIFEST.json
PROJECT_SNAPSHOT.zip
```

### PROJECT_CONTEXT.md

Contains:

- Project folder structure
- Included source files
- Clear file boundaries
- Size-limited project context

### PROJECT_MANIFEST.json

Contains:

- Generation timestamp
- Included file list
- Excluded file information
- Size statistics
- Export metadata

### PROJECT_SNAPSHOT.zip

Contains:

- Generated context file
- Manifest file
- Included project files

## Requirements

### Source Version

- Python 3.9+
- No third-party packages required

## Executable Version

A standalone Windows executable can be generated using PyInstaller.

### Executable Requirements

- Windows 10 or Windows 11
- No Python installation required

The executable bundles the Python runtime and all required standard-library components into a single executable file.

### Notes

- The source version requires Python 3.9+.
- The executable version does not require Python to be installed.
- Windows SmartScreen or antivirus software may display warnings for newly released unsigned executables. This can occur with newly built applications and does not necessarily indicate a problem with the software.

## Usage

### GUI

```bash
py project_context_helper.py
```

Select a project folder and click:

```text
Build Project Context
```

### CLI

```bash
py project_context_helper.py "C:\Path\To\Project"
```

## Generated Files

```text
PROJECT_CONTEXT.md
PROJECT_MANIFEST.json
PROJECT_SNAPSHOT.zip
```

These files are generated in the selected project directory.

## Version

```text
v1.0.0
```

Initial public release.

## Author

Jason Brisart

Part of:

```text
BrisartDevTools
```

## License

See the repository license for licensing information.