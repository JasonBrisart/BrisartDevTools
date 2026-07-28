from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models import (
    FileRecord,
    ScanResult,
    ScanSettings,
    SkipRecord,
)
from utils import (
    count_lines,
    sha256_file,
)

SKIP_OUTSIDE_ROOT = "outside_root"
SKIP_EXTENSION_NOT_INCLUDED = "extension_not_included"
SKIP_FILE_TOO_LARGE = "file_too_large"
SKIP_TOTAL_SIZE_LIMIT = "total_size_limit"
SKIP_SIZE_UNAVAILABLE = "size_unavailable"
SKIP_READ_UNAVAILABLE = "read_unavailable"

SOURCE_COMPLETENESS_FAILURE_REASONS = {
    SKIP_FILE_TOO_LARGE,
    SKIP_TOTAL_SIZE_LIMIT,
    SKIP_SIZE_UNAVAILABLE,
    SKIP_READ_UNAVAILABLE,
}


@dataclass(frozen=True, slots=True)
class FileMeta:
    """
    Cached filesystem metadata for a candidate file.

    This reduces repeated stat calls during scan decisions.
    """

    path: Path
    relative_path: str
    size_bytes: int | None
    suffix: str
    name_lower: str


def relative_string(
    path: Path,
    root: Path,
) -> str:
    """
    Return a safe relative path string.

    If the path is not inside the project root for any reason,
    return the absolute string form instead of crashing.
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def safe_size(
    path: Path,
) -> int | None:
    """
    Return a file size in bytes.

    If the size cannot be read, return None.
    """
    try:
        return path.stat().st_size
    except OSError:
        return None


def build_file_meta(
    path: Path,
    root: Path,
) -> FileMeta:
    """
    Build cached metadata for a candidate path.
    """
    return FileMeta(
        path=path,
        relative_path=relative_string(path, root),
        size_bytes=safe_size(path),
        suffix=path.suffix.lower(),
        name_lower=path.name.lower(),
    )


def can_read_text_file(
    path: Path,
) -> bool:
    """
    Return True if a file can be read as text.

    This does not mean the text is semantically valid.
    It only confirms that the exporter can read and preserve
    the file contents without crashing.
    """
    try:
        path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        return True
    except Exception:
        return False


def exclusion_reason(
    path: Path,
    root: Path,
    settings: ScanSettings,
) -> str | None:
    """
    Return the reason a path should be excluded.

    Returns None when the path is not excluded.
    """
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return SKIP_OUTSIDE_ROOT

    for part in relative_parts:
        if part in settings.exclude_dirs:
            return f"excluded_directory:{part}"

    if path.name in settings.exclude_files:
        return f"excluded_file:{path.name}"

    suffix = path.suffix.lower()
    if suffix in settings.exclude_suffixes:
        return f"excluded_suffix:{suffix}"

    return None


def is_configured_source_file(
    meta: FileMeta,
    settings: ScanSettings,
) -> bool:
    """
    Return True when a file matches the configured source/text
    extension list for the active profile.
    """
    return (
        meta.suffix in settings.include_extensions
        or meta.name_lower in settings.include_extensions
    )


def skip_record(
    meta: FileMeta,
    reason: str,
) -> SkipRecord:
    """
    Build a consistent SkipRecord from cached metadata.
    """
    return SkipRecord(
        relative_path=meta.relative_path,
        reason=reason,
        size_bytes=meta.size_bytes,
    )


def should_include_file(
    path: Path,
    root: Path,
    settings: ScanSettings,
) -> tuple[bool, SkipRecord | None, FileMeta]:
    """
    Return whether a file should be included.

    Also returns a SkipRecord when the file is skipped for
    a known reason and the cached FileMeta used for the decision.
    """
    meta = build_file_meta(path, root)

    if not path.is_file():
        return False, None, meta

    reason = exclusion_reason(path, root, settings)
    if reason:
        return False, skip_record(meta, reason), meta

    if not is_configured_source_file(meta, settings):
        return (
            False,
            skip_record(meta, SKIP_EXTENSION_NOT_INCLUDED),
            meta,
        )

    if meta.size_bytes is None:
        return (
            False,
            skip_record(meta, SKIP_SIZE_UNAVAILABLE),
            meta,
        )

    if meta.size_bytes > settings.max_file_bytes:
        return (
            False,
            skip_record(meta, SKIP_FILE_TOO_LARGE),
            meta,
        )

    if settings.include_file_contents and not can_read_text_file(path):
        return (
            False,
            skip_record(meta, SKIP_READ_UNAVAILABLE),
            meta,
        )

    return True, None, meta


def source_completeness_failures(
    skipped_records: list[SkipRecord],
) -> list[SkipRecord]:
    """
    Return skipped records that represent a failure to preserve
    eligible source files.
    """
    return [
        record
        for record in skipped_records
        if record.reason in SOURCE_COMPLETENESS_FAILURE_REASONS
    ]


def build_source_failure_message(
    failures: list[SkipRecord],
) -> str:
    """
    Build a readable hard-failure message for incomplete archive runs.
    """
    lines = [
        "SOURCE COMPLETENESS CHECK FAILED",
        "",
        "Archive mode requires every eligible source/text file to be captured.",
        "The build was stopped because one or more eligible files were not included.",
        "",
        "Skipped eligible source files:",
    ]

    for record in failures:
        size_display = (
            "unknown"
            if record.size_bytes is None
            else str(record.size_bytes)
        )
        lines.append(
            f"- {record.relative_path} "
            f"({record.reason}, {size_display} bytes)"
        )

    lines.append("")
    lines.append(
        "Increase the archive limits, remove the exclusion, "
        "or fix the unreadable file before building a preservation snapshot."
    )

    return "\n".join(lines)


def build_file_record(
    meta: FileMeta,
    settings: ScanSettings,
) -> FileRecord:
    """
    Build metadata for an included file.
    """
    return FileRecord(
        relative_path=meta.relative_path,
        size_bytes=meta.size_bytes or 0,
        extension=meta.suffix or meta.name_lower,
        sha256=(
            sha256_file(meta.path)
            if settings.include_hashes
            else None
        ),
        line_count=(
            count_lines(meta.path)
            if settings.include_line_counts
            else None
        ),
    )


def collect_included_files(
    root: Path,
    settings: ScanSettings,
) -> ScanResult:
    """
    Collect included files and skipped-file metadata.

    In archive mode, source completeness is enforced.
    If an eligible source/text file is skipped due to size,
    total limit, unreadability, or missing size information,
    the build fails.
    """
    included_paths: list[Path] = []
    included_records: list[FileRecord] = []
    skipped_records: list[SkipRecord] = []
    total_bytes = 0

    for path in sorted(root.rglob("*")):
        include, skip, meta = should_include_file(
            path,
            root,
            settings,
        )

        if skip is not None:
            skipped_records.append(skip)
            continue

        if not include:
            continue

        if meta.size_bytes is None:
            skipped_records.append(
                skip_record(meta, SKIP_SIZE_UNAVAILABLE)
            )
            continue

        if total_bytes + meta.size_bytes > settings.max_total_bytes:
            skipped_records.append(
                skip_record(meta, SKIP_TOTAL_SIZE_LIMIT)
            )
            continue

        included_paths.append(path)
        included_records.append(
            build_file_record(
                meta,
                settings,
            )
        )
        total_bytes += meta.size_bytes

    failures = source_completeness_failures(skipped_records)

    if settings.require_complete_source and failures:
        raise ValueError(
            build_source_failure_message(failures)
        )

    return ScanResult(
        included_paths=tuple(included_paths),
        included_records=tuple(included_records),
        skipped_records=tuple(skipped_records),
        total_included_bytes=total_bytes,
    )


def build_tree(
    root: Path,
    settings: ScanSettings,
) -> str:
    """
    Build a readable folder tree for the selected project.

    Excluded folders and files are not shown in the tree.
    """
    lines: list[str] = [
        root.name + "/"
    ]

    def walk(
        directory: Path,
        prefix: str = "",
    ) -> None:
        try:
            entries = sorted(
                [
                    entry
                    for entry in directory.iterdir()
                    if not exclusion_reason(
                        entry,
                        root,
                        settings,
                    )
                ],
                key=lambda item: (
                    not item.is_dir(),
                    item.name.lower(),
                ),
            )
        except OSError:
            return

        for index, entry in enumerate(entries):
            is_last = index == len(entries) - 1
            connector = (
                "└── "
                if is_last
                else "├── "
            )
            lines.append(
                prefix
                + connector
                + entry.name
                + (
                    "/"
                    if entry.is_dir()
                    else ""
                )
            )

            if entry.is_dir():
                extension = (
                    "    "
                    if is_last
                    else "│   "
                )
                walk(
                    entry,
                    prefix + extension,
                )

    walk(root)
    return "\n".join(lines)