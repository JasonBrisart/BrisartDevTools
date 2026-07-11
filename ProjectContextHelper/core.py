from pathlib import Path
import json

from constants import (
    CONTEXT_FILENAME,
    MANIFEST_FILENAME,
    SETTINGS_FILENAME,
    SNAPSHOT_FILENAME,
    SUMMARY_FILENAME,
)
from exporters import (
    build_manifest,
    build_context_markdown,
    build_summary_text,
    create_snapshot_zip,
)
from models import (
    BuildResult,
    ScanSettings,
)
from scanner import collect_included_files
from utils import (
    timestamp_now,
    timestamp_slug,
    validate_root,
)


def create_context(
    root: Path,
    settings: ScanSettings | None = None,
) -> BuildResult:
    """
    Create a complete Project Context export bundle.
    """
    root = validate_root(root)
    settings = settings or ScanSettings()
    created = timestamp_now()

    base_export_dir = root / settings.output_dir_name

    if settings.timestamped_export_folder:
        export_dir = (
            base_export_dir
            / f"project_context_{timestamp_slug()}"
        )
    else:
        export_dir = base_export_dir

    export_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    context_path = export_dir / CONTEXT_FILENAME
    manifest_path = export_dir / MANIFEST_FILENAME
    summary_path = export_dir / SUMMARY_FILENAME
    settings_path = export_dir / SETTINGS_FILENAME

    snapshot_path = (
        export_dir / SNAPSHOT_FILENAME
        if settings.include_snapshot_zip
        else None
    )

    scan = collect_included_files(
        root,
        settings,
    )

    context_text = build_context_markdown(
        root=root,
        scan=scan,
        settings=settings,
        created=created,
    )

    context_path.write_text(
        context_text,
        encoding="utf-8",
    )

    manifest = build_manifest(
        root=root,
        scan=scan,
        settings=settings,
        created=created,
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary_text = build_summary_text(
        root=root,
        scan=scan,
        settings=settings,
        created=created,
    )

    summary_path.write_text(
        summary_text,
        encoding="utf-8",
    )

    settings_path.write_text(
        json.dumps(
            settings.to_jsonable(),
            indent=2,
        ),
        encoding="utf-8",
    )

    if snapshot_path is not None:
        create_snapshot_zip(
            zip_path=snapshot_path,
            context_path=context_path,
            manifest_path=manifest_path,
            summary_path=summary_path,
            settings_path=settings_path,
            scan=scan,
            root=root,
        )

    return BuildResult(
        export_dir=export_dir,
        context_path=context_path,
        manifest_path=manifest_path,
        summary_path=summary_path,
        settings_path=settings_path,
        snapshot_path=snapshot_path,
        included_count=len(scan.included_records),
        skipped_count=len(scan.skipped_records),
        total_included_bytes=scan.total_included_bytes,
    )