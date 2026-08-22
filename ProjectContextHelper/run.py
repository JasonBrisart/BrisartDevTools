"""
Project Context Helper - Entry Point
This is the ONLY file meant to be run directly. Everything else lives
in a purpose-built subfolder:
    core/      the scan + export engine
    services/  stateful support services (app settings, build history,
               settings memory, custom profile manager, self-updates)
    cli/       the argparse-based command-line interface
    gui/       the tkinter desktop interface
    docs/      CHANGELOG.md, README.md, and ARCHITECTURE.md

The previous version of this tool (v2.3.5) had run.py containing only
`from cli import main` at the project root, alongside every other
module (constants.py, core.py, cli.py, etc.) flat in the same folder.
This version's run.py additionally bootstraps sys.path so the new
subfolder structure resolves correctly regardless of the working
directory the process is launched from.

Usage:
    python run.py                      Launch the desktop GUI
    python run.py <folder>             Build a context export for <folder>
    python run.py <folder> --profile standard
    python run.py <folder> --git-state
    python run.py <folder> --save-profile "My Profile"
    python run.py <folder> --load-profile "My Profile"
    python run.py --list-profiles
    python run.py --delete-profile "My Profile"
    python run.py --check-updates
    python run.py --help               Show all available CLI options

See docs/ARCHITECTURE.md for the full folder layout and docs/README.md
for a quick-start guide.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli.cli import main

if __name__ == "__main__":
    main()
