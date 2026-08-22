from __future__ import annotations
from dataclasses import (
    asdict,
    dataclass,
    field,
)
from pathlib import Path
from typing import Any

_SETTINGS_SET_FIELDS = (
    "include_extensions",
    "exclude_dirs",
    "exclude_files",
    "exclude_suffixes",
)


@dataclass(slots=True)
class ScanSettings:
    """
    User-adjustable settings for a build run.
    """
    profile: str = "standard"
    output_dir_name: str = "PROJECT_CONTEXT_EXPORTS"
    include_extensions: set[str] = field(default_factory=set)
    exclude_dirs: set[str] = field(default_factory=set)
    exclude_files: set[str] = field(default_factory=set)
    exclude_suffixes: set[str] = field(default_factory=set)
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
    require_complete_source: bool = False
    include_git_state: bool = False
    git_state_commit_limit: int = 5

    def to_jsonable(self) -> dict[str, Any]:
        data = asdict(self)
        for key in _SETTINGS_SET_FIELDS:
            data[key] = sorted(list(data[key]))
        return data

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "ScanSettings":
        data = dict(data)
        for field_name in _SETTINGS_SET_FIELDS:
            if field_name in data:
                data[field_name] = set(data[field_name])
        valid_fields = {
            field_obj.name for field_obj in cls.__dataclass_fields__.values()
        }
        filtered = {key: value for key, value in data.items() if key in valid_fields}
        return cls(**filtered)


@dataclass(frozen=True, slots=True)
class FileRecord:
    relative_path: str
    size_bytes: int
    extension: str
    sha256: str | None = None
    line_count: int | None = None


@dataclass(frozen=True, slots=True)
class SkipRecord:
    relative_path: str
    reason: str
    size_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class ScanResult:
    included_paths: tuple[Path, ...]
    included_records: tuple[FileRecord, ...]
    skipped_records: tuple[SkipRecord, ...]
    total_included_bytes: int


@dataclass(frozen=True, slots=True)
class BuildResult:
    export_dir: Path
    context_path: Path
    manifest_path: Path
    summary_path: Path
    settings_path: Path
    snapshot_path: Path | None
    included_count: int
    skipped_count: int
    total_included_bytes: int
    git_branch: str | None = None
    git_commit_short: str | None = None
    git_is_dirty: bool | None = None
