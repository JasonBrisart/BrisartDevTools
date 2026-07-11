from __future__ import annotations

import datetime
import hashlib
import re

from pathlib import Path


_SECRET_PATTERN = re.compile(
    r"(?i)(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)\s*[:=]"
)


def timestamp_now() -> str:
    """
    Return a human-readable timestamp.
    """
    return (
        datetime.datetime.now()
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S %z")
    )


def timestamp_slug() -> str:
    """
    Return a filesystem-safe timestamp.
    """
    return (
        datetime.datetime.now()
        .astimezone()
        .strftime("%Y%m%d_%H%M%S")
    )


def validate_root(
    root: Path,
) -> Path:
    """
    Validate and normalize a project root.
    """
    root = (
        root.expanduser()
        .resolve()
    )

    if not root.exists():
        raise FileNotFoundError(
            f"Project folder does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Selected path is not a folder: {root}"
        )

    return root


def normalize_extension(
    value: str,
) -> str:
    """
    Normalize a file extension.
    """
    value = (
        value.strip()
        .lower()
    )

    if not value:
        return value

    if value.startswith("."):
        return value

    return f".{value}"


def safe_read(
    path: Path,
    redact_sensitive_lines: bool = True,
) -> str:
    """
    Safely read a text file.

    Optionally redact likely secret values.
    """
    try:
        text = path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception as exc:
        return f"[[Could not read file: {exc}]]"

    if not redact_sensitive_lines:
        return text

    redacted_lines: list[str] = []

    for line in text.splitlines():
        if _SECRET_PATTERN.search(line):
            redacted_lines.append(
                "[[REDACTED POSSIBLE SECRET LINE]]"
            )

        else:
            redacted_lines.append(line)

    return "\n".join(redacted_lines)


def count_lines(
    path: Path,
) -> int | None:
    """
    Count lines in a text file.
    """
    try:
        return len(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        )

    except Exception:
        return None


def sha256_file(
    path: Path,
) -> str | None:
    """
    Generate SHA256 checksum.
    """
    try:
        hasher = hashlib.sha256()

        with path.open("rb") as handle:
            for chunk in iter(
                lambda: handle.read(
                    1024 * 1024
                ),
                b"",
            ):
                hasher.update(chunk)

        return hasher.hexdigest()

    except Exception:
        return None


def language_hint(
    path: Path,
) -> str:
    """
    Determine markdown code block language.
    """
    suffix = path.suffix.lower()

    mapping = {
        ".py": "python",
        ".json": "json",
        ".csv": "csv",
        ".txt": "text",
        ".md": "markdown",
        ".rst": "rst",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
        ".css": "css",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".sql": "sql",
        ".xml": "xml",
        ".bat": "bat",
        ".ps1": "powershell",
        ".sh": "bash",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".r": "r",
        ".pl": "perl",
        ".lua": "lua",
    }

    if path.name.lower() in {
        ".gitignore",
        ".dockerignore",
    }:
        return "text"

    return mapping.get(
        suffix,
        "text",
    )