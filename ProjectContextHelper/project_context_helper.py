#!/usr/bin/env python3
"""
Project Context Helper
----------------------

A tiny no-dependency utility that packages a project folder into a readable
Markdown context file, a compact JSON manifest, and a local ZIP snapshot.

What it does:
1. Scans a selected project folder recursively.
2. Builds PROJECT_CONTEXT.md containing:
   - folder tree
   - selected source/config files
   - clear file boundaries
3. Builds PROJECT_MANIFEST.json with included/skipped file details.
4. Builds PROJECT_SNAPSHOT.zip for local backup/sharing.

Usage:
- Double-click the script to launch the GUI.
- Or run from the command line:

    py project_context_helper.py
    py project_context_helper.py "C:\\Path\\To\\Project"

No internet.
No third-party packages.
Works with standard Python.

Author:
Jason Brisart

Repository:
https://github.com/JasonBrisart/BrisartDevTools
"""

from __future__ import annotations

import datetime
import json
import sys
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox


APP_NAME = "Project Context Helper"
APP_VERSION = "1.0.0"

AUTHOR = "Jason Brisart"
REPOSITORY_NAME = "BrisartDevTools"
REPOSITORY_URL = "https://github.com/JasonBrisart/BrisartDevTools"

CONTEXT_FILENAME = "PROJECT_CONTEXT.md"
MANIFEST_FILENAME = "PROJECT_MANIFEST.json"
SNAPSHOT_FILENAME = "PROJECT_SNAPSHOT.zip"

DEFAULT_EXTENSIONS = {
    ".py",
    ".json",
    ".csv",
    ".txt",
    ".md",
    ".toml",
    ".ini",
    ".cfg",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".js",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "build",
    "dist",
    ".idea",
    ".vscode",
    "updates",
}

DEFAULT_EXCLUDE_FILES = {
    CONTEXT_FILENAME,
    MANIFEST_FILENAME,
    SNAPSHOT_FILENAME,
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
}

DEFAULT_EXCLUDE_SUFFIXES = {
    ".pem",
    ".key",
    ".crt",
    ".pfx",
    ".p12",
}

MAX_FILE_BYTES = 250_000
MAX_TOTAL_BYTES = 2_500_000


def timestamp_now() -> str:
    """
    Return a timezone-aware timestamp string.
    """
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def validate_root(root: Path) -> Path:
    """
    Resolve and validate the selected project root.
    """
    root = root.expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Selected path is not a folder: {root}")

    return root


def is_excluded(path: Path, root: Path) -> bool:
    """
    Return True if a path should be excluded from scanning/output.
    """
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True

    if path.is_symlink():
        return True

    if any(part in DEFAULT_EXCLUDE_DIRS for part in rel_parts):
        return True

    if path.name in DEFAULT_EXCLUDE_FILES:
        return True

    if path.suffix.lower() in DEFAULT_EXCLUDE_SUFFIXES:
        return True

    return False


def should_include_file(path: Path, root: Path) -> bool:
    """
    Return True if a file should be included in PROJECT_CONTEXT.md and the ZIP.
    """
    if is_excluded(path, root):
        return False

    if not path.is_file():
        return False

    if path.suffix.lower() not in DEFAULT_EXTENSIONS:
        return False

    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return False
    except OSError:
        return False

    return True


def build_tree(root: Path) -> str:
    """
    Build a readable folder tree for the selected project.
    """
    lines: list[str] = []

    for path in sorted(root.rglob("*")):
        if is_excluded(path, root):
            continue

        try:
            rel = path.relative_to(root)
        except ValueError:
            continue

        depth = len(rel.parts) - 1
        prefix = "  " * depth + "- "
        label = f"{path.name}/" if path.is_dir() else path.name

        lines.append(prefix + label)

    return "\n".join(lines)


def safe_read(path: Path) -> str:
    """
    Read a text file safely using UTF-8, replacing invalid characters if needed.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[[Could not read file: {exc}]]"


def language_hint(path: Path) -> str:
    """
    Return a Markdown code-fence language hint based on file extension.
    """
    suffix = path.suffix.lower()

    hints = {
        ".py": "python",
        ".json": "json",
        ".csv": "csv",
        ".txt": "text",
        ".md": "markdown",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
        ".css": "css",
        ".js": "javascript",
    }

    return hints.get(suffix, "text")


def collect_included_files(root: Path) -> tuple[list[Path], list[str], int]:
    """
    Collect files that should be included, respecting file and total size limits.
    """
    all_files = [
        path
        for path in sorted(root.rglob("*"))
        if should_include_file(path, root)
    ]

    included: list[Path] = []
    skipped_after_limit: list[str] = []
    total_bytes = 0

    for path in all_files:
        try:
            size = path.stat().st_size
        except OSError:
            continue

        if total_bytes + size > MAX_TOTAL_BYTES:
            skipped_after_limit.append(str(path.relative_to(root)))
            continue

        included.append(path)
        total_bytes += size

    return included, skipped_after_limit, total_bytes


def build_manifest(
    root: Path,
    included: list[Path],
    skipped_after_limit: list[str],
    total_bytes: int,
    created: str,
) -> dict:
    """
    Build the JSON manifest metadata.
    """
    return {
        "created": created,
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "author": AUTHOR,
        "repository_name": REPOSITORY_NAME,
        "repository_url": REPOSITORY_URL,
        "root": str(root),
        "included_count": len(included),
        "included_bytes": total_bytes,
        "max_file_bytes": MAX_FILE_BYTES,
        "max_total_bytes": MAX_TOTAL_BYTES,
        "included_files": [str(path.relative_to(root)) for path in included],
        "skipped_after_total_limit": skipped_after_limit,
        "excluded_dirs": sorted(DEFAULT_EXCLUDE_DIRS),
        "excluded_files": sorted(DEFAULT_EXCLUDE_FILES),
        "excluded_suffixes": sorted(DEFAULT_EXCLUDE_SUFFIXES),
        "included_extensions": sorted(DEFAULT_EXTENSIONS),
    }


def build_context_markdown(
    root: Path,
    included: list[Path],
    skipped_after_limit: list[str],
    created: str,
) -> str:
    """
    Build the full PROJECT_CONTEXT.md content.
    """
    chunks: list[str] = []

    chunks.append("# Project Context\n\n")
    chunks.append(f"Generated: {created}\n\n")
    chunks.append(f"Generated by: {APP_NAME} v{APP_VERSION}\n\n")
    chunks.append(f"Author: {AUTHOR}\n\n")
    chunks.append(f"Part of: {REPOSITORY_NAME}\n\n")
    chunks.append(f"Repository: {REPOSITORY_URL}\n\n")
    chunks.append(f"Root: `{root}`\n")

    chunks.append(
        "\n## How to use this file\n\n"
        "This Markdown file contains the selected project folder tree and selected "
        "source/configuration files. It can be used for review, debugging, documentation, "
        "backup, AI-assisted development, or patch preparation.\n"
    )

    chunks.append(
        "\n## Limits\n\n"
        f"- Maximum individual file size: `{MAX_FILE_BYTES}` bytes\n"
        f"- Maximum total included content size: `{MAX_TOTAL_BYTES}` bytes\n"
        "- Some sensitive file types and common build/cache folders are excluded by default.\n"
    )

    chunks.append("\n## Folder Tree\n\n")
    chunks.append("```text\n")
    chunks.append(build_tree(root))
    chunks.append("\n```\n")

    chunks.append("\n## Included Files\n")

    for path in included:
        rel = path.relative_to(root)
        content = safe_read(path)
        hint = language_hint(path)

        chunks.append(f"\n---\n\n### File: `{rel}`\n\n")
        chunks.append(f"````{hint}\n")
        chunks.append(content)
        chunks.append("\n````\n")

    if skipped_after_limit:
        chunks.append("\n## Files skipped because project context reached the total size limit\n\n")

        for name in skipped_after_limit:
            chunks.append(f"- `{name}`\n")

    return "".join(chunks)


def create_snapshot_zip(
    zip_path: Path,
    context_path: Path,
    manifest_path: Path,
    included: list[Path],
    root: Path,
) -> None:
    """
    Create PROJECT_SNAPSHOT.zip containing the context file, manifest file, and included files.
    """
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(context_path, context_path.name)
        archive.write(manifest_path, manifest_path.name)

        for path in included:
            archive.write(path, str(path.relative_to(root)))


def create_context(root: Path) -> tuple[Path, Path, Path]:
    """
    Create PROJECT_CONTEXT.md, PROJECT_MANIFEST.json, and PROJECT_SNAPSHOT.zip.
    """
    root = validate_root(root)
    created = timestamp_now()

    context_path = root / CONTEXT_FILENAME
    manifest_path = root / MANIFEST_FILENAME
    zip_path = root / SNAPSHOT_FILENAME

    included, skipped_after_limit, total_bytes = collect_included_files(root)

    manifest = build_manifest(
        root=root,
        included=included,
        skipped_after_limit=skipped_after_limit,
        total_bytes=total_bytes,
        created=created,
    )

    context_markdown = build_context_markdown(
        root=root,
        included=included,
        skipped_after_limit=skipped_after_limit,
        created=created,
    )

    context_path.write_text(context_markdown, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    create_snapshot_zip(
        zip_path=zip_path,
        context_path=context_path,
        manifest_path=manifest_path,
        included=included,
        root=root,
    )

    return context_path, manifest_path, zip_path


def run_gui() -> None:
    """
    Launch the Tkinter GUI.
    """
    root = tk.Tk()
    root.title(f"{APP_NAME} v{APP_VERSION}")
    root.geometry("660x440")
    root.minsize(600, 410)

    selected_dir = tk.StringVar(value=str(Path.cwd()))
    status = tk.StringVar(value="Select your project folder, then click Build Project Context.")

    def browse() -> None:
        folder = filedialog.askdirectory(
            initialdir=selected_dir.get(),
            title="Select project folder",
        )

        if folder:
            selected_dir.set(folder)

    def build() -> None:
        try:
            folder = Path(selected_dir.get())
            context_path, manifest_path, zip_path = create_context(folder)

            status.set(
                "Created:\n"
                f"{context_path}\n"
                f"{manifest_path}\n"
                f"{zip_path}"
            )

            messagebox.showinfo(
                "Done",
                "Project context files created successfully.",
            )

        except Exception as exc:
            status.set(f"Error: {exc}")
            messagebox.showerror("Error", str(exc))

    title = tk.Label(
        root,
        text=APP_NAME,
        font=("Segoe UI", 16, "bold"),
    )
    title.pack(pady=(14, 4))

    version = tk.Label(
        root,
        text=f"v{APP_VERSION}",
        font=("Segoe UI", 9),
    )
    version.pack(pady=(0, 2))

    author_label = tk.Label(
        root,
        text=f"Created by {AUTHOR}",
        font=("Segoe UI", 8),
        fg="gray",
        justify="center",
    )
    author_label.pack(pady=(0, 2))

    repo_label = tk.Label(
        root,
        text=f"{REPOSITORY_NAME}\n{REPOSITORY_URL}",
        font=("Segoe UI", 8),
        fg="gray",
        justify="center",
    )
    repo_label.pack(pady=(0, 8))

    info = tk.Label(
        root,
        text=(
            "Create one Markdown file with your project tree and selected source files, "
            "plus a JSON manifest and local ZIP snapshot."
        ),
        wraplength=590,
        justify="center",
    )
    info.pack(pady=6)

    frame = tk.Frame(root)
    frame.pack(pady=12, fill="x", padx=24)

    entry = tk.Entry(frame, textvariable=selected_dir)
    entry.pack(side="left", fill="x", expand=True)

    browse_button = tk.Button(frame, text="Browse", command=browse)
    browse_button.pack(side="left", padx=(8, 0))

    build_button = tk.Button(
        root,
        text="Build Project Context",
        command=build,
        height=2,
        width=30,
    )
    build_button.pack(pady=12)

    status_label = tk.Label(
        root,
        textvariable=status,
        wraplength=590,
        justify="left",
        anchor="w",
    )
    status_label.pack(pady=10, padx=24, fill="x")

    root.mainloop()


def run_cli() -> None:
    """
    Run from the command line.

    If a folder argument is provided, scan that folder.
    Otherwise, scan the current working directory.
    """
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    context_path, manifest_path, zip_path = create_context(folder)

    print("Created:")
    print(context_path)
    print(manifest_path)
    print(zip_path)


def main() -> None:
    """
    Entry point.

    CLI mode:
        py project_context_helper.py "C:\\Path\\To\\Project"

    GUI mode:
        py project_context_helper.py
    """
    if len(sys.argv) > 1:
        run_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()