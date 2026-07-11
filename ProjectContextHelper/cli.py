from pathlib import Path
import argparse

from constants import (
    APP_NAME,
    APP_VERSION,
    VALID_PROFILES,
    settings_for_profile,
)

from core import create_context

# GUI package import
from gui.main_gui import run_gui

from updater import (
    check_for_updates,
    open_releases_page,
)

from utils import normalize_extension


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION}"
    )

    parser.add_argument(
        "root",
        nargs="?",
        help="Project folder to export. If omitted, GUI mode launches.",
    )

    parser.add_argument(
        "--profile",
        choices=sorted(VALID_PROFILES),
        default="standard",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
    )

    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--max-total-bytes",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--extensions",
        default=None,
    )

    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--exclude-file",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--no-zip",
        action="store_true",
    )

    parser.add_argument(
        "--no-redact",
        action="store_true",
    )

    parser.add_argument(
        "--no-hashes",
        action="store_true",
    )

    parser.add_argument(
        "--no-line-counts",
        action="store_true",
    )

    parser.add_argument(
        "--no-tree",
        action="store_true",
    )

    parser.add_argument(
        "--no-index",
        action="store_true",
    )

    parser.add_argument(
        "--no-contents",
        action="store_true",
    )

    parser.add_argument(
        "--no-skipped-details",
        action="store_true",
    )

    parser.add_argument(
        "--skipped-details-limit",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--flat-output",
        action="store_true",
    )

    parser.add_argument(
        "--check-updates",
        action="store_true",
    )

    parser.add_argument(
        "--open-releases",
        action="store_true",
    )

    return parser


def settings_from_args(args):
    settings = settings_for_profile(args.profile)

    if args.output_dir:
        settings.output_dir_name = args.output_dir

    if args.max_file_bytes is not None:
        settings.max_file_bytes = args.max_file_bytes

    if args.max_total_bytes is not None:
        settings.max_total_bytes = args.max_total_bytes

    if args.extensions:
        settings.include_extensions = {
            normalize_extension(item)
            for item in args.extensions.split(",")
            if item.strip()
        }

    if args.exclude_dir:
        settings.exclude_dirs.update(args.exclude_dir)

    if args.exclude_file:
        settings.exclude_files.update(args.exclude_file)

    if args.no_zip:
        settings.include_snapshot_zip = False

    if args.no_redact:
        settings.redact_sensitive_lines = False

    if args.no_hashes:
        settings.include_hashes = False

    if args.no_line_counts:
        settings.include_line_counts = False

    if args.no_tree:
        settings.include_folder_tree = False

    if args.no_index:
        settings.include_file_index = False

    if args.no_contents:
        settings.include_file_contents = False

    if args.no_skipped_details:
        settings.include_skipped_details = False

    if args.skipped_details_limit is not None:
        settings.skipped_details_limit = max(
            0,
            args.skipped_details_limit,
        )

    if args.flat_output:
        settings.timestamped_export_folder = False

    return settings


def run_update_check(
    open_page_when_available: bool = False,
) -> None:
    info = check_for_updates()

    print(f"{APP_NAME} v{APP_VERSION}")
    print()
    print(info.message)

    if info.update_available:
        print(f"Release page: {info.release_url}")

        if open_page_when_available:
            open_releases_page(info.release_url)


def run_cli() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.check_updates:
        run_update_check(
            open_page_when_available=args.open_releases,
        )

        if not args.root:
            return

    if not args.root:
        run_gui()
        return

    settings = settings_from_args(args)

    result = create_context(
        Path(args.root),
        settings=settings,
    )

    print(f"{APP_NAME} v{APP_VERSION}")
    print()
    print("Build completed")
    print("----------------")
    print(f"Export Folder: {result.export_dir}")
    print(f"Context File : {result.context_path}")
    print(f"Manifest File: {result.manifest_path}")
    print(f"Summary File : {result.summary_path}")
    print(f"Settings File: {result.settings_path}")

    if result.snapshot_path:
        print(f"Snapshot Zip : {result.snapshot_path}")

    print()
    print(f"Included Files: {result.included_count}")
    print(f"Skipped Files : {result.skipped_count}")
    print(f"Included Bytes: {result.total_included_bytes}")


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()