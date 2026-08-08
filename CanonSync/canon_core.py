#!/usr/bin/env python3
"""
canon_core.py
-------------
Engine for CanonSync: keep a set of canonical files (the "canon") in sync
across many git repos, from a single source of truth.

CanonSync replaces the earlier gitignore-only tool. It syncs any number of
declared files -- .gitignore, .editorconfig, .gitattributes, LICENSE, and
so on -- each in one of two modes:

- "block":  Inject the canonical content into a delimited MANAGED BLOCK
            inside the destination file, preserving whatever that repo
            added around the block. Used for files that legitimately have
            both shared and repo-specific parts (.gitignore, .editorconfig,
            .gitattributes). Requires a '#'-comment-friendly destination.

- "whole":  Replace the ENTIRE destination file with the canonical
            content. Used for files that have no repo-specific part, such
            as LICENSE. Nothing in the repo's copy is preserved.

What to sync, and in which mode, is declared in canon.config.json. This
module is pure logic with no UI; it is imported by the GUI and can also be
run as a CLI.

Design goals:
- Pure standard library. No third-party dependencies.
- Local-first / offline. Never touches the network.
- Safe by default. Callers preview a plan first; nothing is written until
  an explicit apply. "whole" items are disabled by default in the config
  so a license can never be overwritten unintentionally.
- Idempotent. Re-running with no source change writes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

APP_NAME = "CanonSync"
APP_VERSION = "1.0.0"

BEGIN_MARKER = "# >>> CANONICAL (managed by CanonSync) - DO NOT EDIT >>>"
END_MARKER = "# <<< CANONICAL <<<"
REPO_SPECIFIC_SEPARATOR = "# --- repo-specific (not managed) ---"

MODE_BLOCK = "block"
MODE_WHOLE = "whole"

STATUS_CREATE = "create"
STATUS_UPDATE = "update"
STATUS_UNCHANGED = "unchanged"
STATUS_MISSING = "missing"
STATUS_SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config(config_path: Path) -> dict:
    """
    Load canon.config.json and resolve each item's source path relative to
    the config file's own directory.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    base = config_path.parent
    for item in data.get("items", []):
        item["_source_path"] = (base / item["source"]).resolve()
    return data


def enabled_items(config: dict, only: set[str] | None = None) -> list[dict]:
    """
    Return the config items that are enabled (optionally filtered to a set
    of item names selected in the UI).
    """
    items = []
    for item in config.get("items", []):
        if not item.get("enabled", True):
            continue
        if only is not None and item["name"] not in only:
            continue
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# Block-mode helpers
# ---------------------------------------------------------------------------
def build_managed_block(body: str) -> str:
    """
    Wrap canonical body text in the begin/end markers.
    """
    return f"{BEGIN_MARKER}\n{body}\n{END_MARKER}"


def split_existing(text: str) -> tuple[str | None, str, str]:
    """
    Split a destination file into (marker_state, before, after). marker_state
    is None when no managed block exists, else "present".
    """
    if BEGIN_MARKER not in text or END_MARKER not in text:
        return None, text, ""
    before, rest = text.split(BEGIN_MARKER, 1)
    _old, after = rest.split(END_MARKER, 1)
    return "present", before.rstrip("\n"), after.lstrip("\n")


def compose_block(existing_text: str, managed_block: str) -> str:
    """
    Produce new destination text for block mode, preserving repo-specific
    content and refreshing (or inserting) the managed block.
    """
    marker_state, before, after = split_existing(existing_text)
    if marker_state is not None:
        parts: list[str] = []
        if before.strip():
            parts.append(before.rstrip("\n"))
            parts.append("")
        parts.append(managed_block)
        if after.strip():
            parts.append("")
            parts.append(after.strip("\n"))
        return "\n".join(parts).strip("\n") + "\n"

    existing = existing_text.strip("\n")
    if not existing:
        return managed_block + "\n"
    return (
        managed_block + "\n\n" + REPO_SPECIFIC_SEPARATOR + "\n" + existing + "\n"
    )


def normalize_whole(body: str) -> str:
    """
    Normalize whole-mode content to a single trailing newline.
    """
    return body.rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
def read_source(item: dict) -> str:
    """
    Read the canonical source text for an item.
    """
    path: Path = item["_source_path"]
    if not path.exists():
        raise FileNotFoundError(f"Source for '{item['name']}' not found: {path}")
    return path.read_text(encoding="utf-8").strip("\n")


def plan_item_for_repo(repo: Path, item: dict, source_text: str) -> tuple[str, str | None]:
    """
    Decide the action for one canonical item in one repo, without writing.

    Returns (status, new_text). new_text is None when nothing should be
    written.
    """
    if not repo.exists():
        return STATUS_MISSING, None
    dest = repo / item["dest"]
    mode = item.get("mode", MODE_BLOCK)

    if mode == MODE_WHOLE:
        new_text = normalize_whole(source_text)
        if not dest.exists():
            return STATUS_CREATE, new_text
        if dest.read_text(encoding="utf-8") == new_text:
            return STATUS_UNCHANGED, None
        return STATUS_UPDATE, new_text

    # Default: block mode.
    managed_block = build_managed_block(source_text)
    if not dest.exists():
        return STATUS_CREATE, compose_block("", managed_block)
    current = dest.read_text(encoding="utf-8")
    new_text = compose_block(current, managed_block)
    if new_text == current:
        return STATUS_UNCHANGED, None
    return STATUS_UPDATE, new_text


def discover_repos(root: Path) -> list[Path]:
    """
    Find git repos: root itself if it is one, plus immediate subdirs that
    contain a .git entry. De-duplicated, order preserved.
    """
    found: list[Path] = []
    if (root / ".git").exists():
        found.append(root)
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / ".git").exists():
                found.append(child)
    seen: set[Path] = set()
    unique: list[Path] = []
    for repo in found:
        if repo not in seen:
            seen.add(repo)
            unique.append(repo)
    return unique


def sync(
    config: dict,
    repos: list[Path],
    apply: bool,
    only: set[str] | None = None,
) -> list[dict]:
    """
    Plan (and optionally apply) every enabled canonical item across repos.

    Returns a flat list of result dicts:
        {"repo": Path, "item": str, "dest": str, "status": str, "written": bool}
    """
    items = enabled_items(config, only=only)
    # Pre-read sources once.
    sources = {item["name"]: read_source(item) for item in items}

    results: list[dict] = []
    for repo in repos:
        for item in items:
            status, new_text = plan_item_for_repo(repo, item, sources[item["name"]])
            written = False
            if (
                apply
                and new_text is not None
                and status in (STATUS_CREATE, STATUS_UPDATE)
            ):
                (repo / item["dest"]).write_text(new_text, encoding="utf-8")
                written = True
            results.append(
                {
                    "repo": repo,
                    "item": item["name"],
                    "dest": item["dest"],
                    "status": status,
                    "written": written,
                }
            )
    return results


def summarize(results: list[dict]) -> dict:
    """
    Count results by status.
    """
    counts = {
        STATUS_CREATE: 0,
        STATUS_UPDATE: 0,
        STATUS_UNCHANGED: 0,
        STATUS_MISSING: 0,
        STATUS_SKIPPED: 0,
    }
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _resolve_targets(repo_args: list[str], discover: str) -> list[Path]:
    targets: list[Path] = []
    for repo in repo_args:
        targets.append(Path(repo).expanduser().resolve())
    if discover:
        targets.extend(discover_repos(Path(discover).expanduser().resolve()))
    seen: set[Path] = set()
    unique: list[Path] = []
    for target in targets:
        if target not in seen:
            seen.add(target)
            unique.append(target)
    return unique


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="canon_core.py",
        description=f"{APP_NAME} v{APP_VERSION} - sync canonical files across repos.",
    )
    parser.add_argument("--config", default="canon.config.json", help="Path to canon.config.json.")
    parser.add_argument("--repo", action="append", default=[], help="A target repo root (repeatable).")
    parser.add_argument("--discover", default="", help="Parent folder to auto-discover repos in.")
    parser.add_argument("--only", default="", help="Comma-separated item names to sync (default: all enabled).")
    parser.add_argument("--apply", action="store_true", help="Write changes. Without it, a dry run.")
    return parser


def _cli(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    config = load_config(Path(args.config).expanduser().resolve())
    targets = _resolve_targets(args.repo, args.discover)
    only = {s.strip() for s in args.only.split(",") if s.strip()} or None

    print(f"{APP_NAME} v{APP_VERSION}")
    print(f"Mode:  {'APPLY' if args.apply else 'dry run (nothing written)'}")
    print(f"Items: {', '.join(i['name'] for i in enabled_items(config, only)) or '(none enabled)'}")
    print(f"Repos: {len(targets)}")
    print()
    if not targets:
        print("No target repos. Pass --repo PATH and/or --discover PARENT_DIR.")
        return 1

    results = sync(config, targets, apply=args.apply, only=only)
    label = {
        STATUS_CREATE: "CREATE",
        STATUS_UPDATE: "UPDATE",
        STATUS_UNCHANGED: "ok",
        STATUS_MISSING: "MISSING",
        STATUS_SKIPPED: "skip",
    }
    for r in results:
        if r["status"] == STATUS_UNCHANGED:
            continue
        print(f"- {label[r['status']]:<8}{r['item']:<14}{r['repo']}")
    c = summarize(results)
    print()
    print(
        f"Summary: {c[STATUS_CREATE]} create, {c[STATUS_UPDATE]} update, "
        f"{c[STATUS_UNCHANGED]} unchanged, {c[STATUS_MISSING]} missing."
    )
    if not args.apply and (c[STATUS_CREATE] or c[STATUS_UPDATE]):
        print("Dry run only. Re-run with --apply to write these changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
