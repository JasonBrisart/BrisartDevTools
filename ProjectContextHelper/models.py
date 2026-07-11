from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
    asdict,
)
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ScanSettings:
    """
    User-adjustable settings for a build run.
    """

    profile: str = "standard"
    output_dir_name: str = "PROJECT_CONTEXT_EXPORTS"

    include_extensions: set[str] = field(
        default_factory=set
    )
    exclude_dirs: set[str] = field(
        default_factory=set
    )
    exclude_files: set[str] = field(
        default_factory=set
    )
    exclude_suffixes: set[str] = field(
        default_factory=set
    )

    max_file_bytes: int = 350_000
    max_total_bytes: int = 5_000_000

    include_snapshot_zip: bool = True
    redact_sensitive_lines: bool = True
    include_hashes: bool = True
    include_line_counts: bool = True
    include_folder_tree: bool = True
    include_file_index: bool = True
    include_file_contents: bool = True
    include_skipped_details: bool = True

    timestamped_export_folder: bool = True
    skipped_details_limit: int = 250

    def to_jsonable(self) -> dict[str, Any]:
        """
        Convert to JSON-safe dictionary.
        """
        data = asdict(self)

        for key in (
            "include_extensions",
            "exclude_dirs",
            "exclude_files",
            "exclude_suffixes",
        ):
            data[key] = sorted(
                list(data[key])
            )

        return data


@dataclass(slots=True)
class FileRecord:
    """
    Metadata for an included file.
    """

    relative_path: str
    size_bytes: int
    extension: str
    sha256: str | None = None
    line_count: int | None = None


@dataclass(slots=True)
class SkipRecord:
    """
    Metadata describing why a file was skipped.
    """

    relative_path: str
    reason: str
    size_bytes: int | None = None


@dataclass(slots=True)
class ScanResult:
    """
    Scanner output.
    """

    included_paths: list[Path]
    included_records: list[FileRecord]
    skipped_records: list[SkipRecord]
    total_included_bytes: int


@dataclass(slots=True)
class BuildResult:
    """
    Final export result.
    """

    export_dir: Path
    context_path: Path
    manifest_path: Path
    summary_path: Path
    settings_path: Path
    snapshot_path: Path | None
    included_count: int
    skipped_count: int
    total_included_bytes: int