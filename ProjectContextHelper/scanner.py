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
        return str(
            path.relative_to(root)
        )

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
        return "outside_root"

    for part in relative_parts:
        if part in settings.exclude_dirs:
            return f"excluded_directory:{part}"

    if path.name in settings.exclude_files:
        return f"excluded_file:{path.name}"

    suffix = path.suffix.lower()

    if suffix in settings.exclude_suffixes:
        return f"excluded_suffix:{suffix}"

    return None


def should_include_file(
    path: Path,
    root: Path,
    settings: ScanSettings,
) -> tuple[bool, SkipRecord | None]:
    """
    Return whether a file should be included.

    Also returns a SkipRecord when the file is skipped for a known reason.
    """
    relative_path = relative_string(
        path,
        root,
    )

    if not path.is_file():
        return False, None

    reason = exclusion_reason(
        path,
        root,
        settings,
    )

    if reason:
        return False, SkipRecord(
            relative_path=relative_path,
            reason=reason,
            size_bytes=safe_size(path),
        )

    suffix = path.suffix.lower()
    name = path.name.lower()

    if (
        suffix not in settings.include_extensions
        and name not in settings.include_extensions
    ):
        return False, SkipRecord(
            relative_path=relative_path,
            reason="extension_not_included",
            size_bytes=safe_size(path),
        )

    size = safe_size(path)

    if size is None:
        return False, SkipRecord(
            relative_path=relative_path,
            reason="size_unavailable",
            size_bytes=None,
        )

    if size > settings.max_file_bytes:
        return False, SkipRecord(
            relative_path=relative_path,
            reason="file_too_large",
            size_bytes=size,
        )

    return True, None


def collect_included_files(
    root: Path,
    settings: ScanSettings,
) -> ScanResult:
    """
    Collect included files and skipped-file metadata.
    """
    included_paths: list[Path] = []
    included_records: list[FileRecord] = []
    skipped_records: list[SkipRecord] = []

    total_bytes = 0

    for path in sorted(root.rglob("*")):
        include, skip = should_include_file(
            path,
            root,
            settings,
        )

        if skip is not None:
            skipped_records.append(skip)
            continue

        if not include:
            continue

        size = safe_size(path)

        if size is None:
            skipped_records.append(
                SkipRecord(
                    relative_path=relative_string(
                        path,
                        root,
                    ),
                    reason="size_unavailable",
                    size_bytes=None,
                )
            )
            continue

        if total_bytes + size > settings.max_total_bytes:
            skipped_records.append(
                SkipRecord(
                    relative_path=relative_string(
                        path,
                        root,
                    ),
                    reason="total_size_limit",
                    size_bytes=size,
                )
            )
            continue

        included_paths.append(path)

        included_records.append(
            FileRecord(
                relative_path=relative_string(
                    path,
                    root,
                ),
                size_bytes=size,
                extension=path.suffix.lower() or path.name.lower(),
                sha256=(
                    sha256_file(path)
                    if settings.include_hashes
                    else None
                ),
                line_count=count_lines(path),
            )
        )

        total_bytes += size

    return ScanResult(
        included_paths=included_paths,
        included_records=included_records,
        skipped_records=skipped_records,
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