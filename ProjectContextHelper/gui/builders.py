from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from constants import (
    DEFAULT_PROFILE,
    EXPORTS_DIRNAME,
    PROFILE_ARCHIVE,
    PROFILE_STANDARD,
    settings_for_profile,
)
from core import create_context
from models import (
    BuildResult,
    ScanSettings,
)
@dataclass(slots=True)
class GuiState:
    """
    Shared GUI state.
    This keeps tkinter variables in one place so the tab files
    do not need to create duplicate settings.
    """
    selected_folder: tk.StringVar
    profile_var: tk.StringVar
    output_dir_var: tk.StringVar
    max_file_mb_var: tk.StringVar
    max_total_mb_var: tk.StringVar
    skipped_limit_var: tk.StringVar
    include_zip_var: tk.BooleanVar
    redact_var: tk.BooleanVar
    include_hashes_var: tk.BooleanVar
    include_line_counts_var: tk.BooleanVar
    include_tree_var: tk.BooleanVar
    include_index_var: tk.BooleanVar
    include_contents_var: tk.BooleanVar
    include_skipped_details_var: tk.BooleanVar
    timestamped_folder_var: tk.BooleanVar
    open_after_build_var: tk.BooleanVar
    check_updates_startup_var: tk.BooleanVar
    auto_install_var: tk.BooleanVar
    status_text: tk.StringVar
    last_export_dir: Path | None = None
def bytes_to_mb_text(
    value: int,
) -> str:
    """
    Convert bytes to a compact decimal MB string for the GUI.
    """
    mb_value = value / 1_000_000
    if mb_value.is_integer():
        return str(int(mb_value))
    return str(mb_value).rstrip("0").rstrip(".")
def make_bool_var(
    value: bool,
) -> tk.BooleanVar:
    """
    Create a BooleanVar from a normal bool.
    """
    return tk.BooleanVar(value=bool(value))
def make_gui_state() -> GuiState:
    """
    Create the default GUI state.
    Default startup profile is archive (the maximum-preservation mode).
    Profile-controlled values are loaded from constants.py through
    settings_for_profile() so the GUI and CLI share one source of truth.
    Both update-related toggles default to False: checking for
    updates and, separately, auto-installing them in place are both
    opt-in rather than on by default.
    """
    settings = settings_for_profile(DEFAULT_PROFILE)
    return GuiState(
        selected_folder=tk.StringVar(value=""),
        profile_var=tk.StringVar(value=settings.profile),
        output_dir_var=tk.StringVar(
            value=settings.output_dir_name or EXPORTS_DIRNAME
        ),
        max_file_mb_var=tk.StringVar(
            value=bytes_to_mb_text(settings.max_file_bytes)
        ),
        max_total_mb_var=tk.StringVar(
            value=bytes_to_mb_text(settings.max_total_bytes)
        ),
        skipped_limit_var=tk.StringVar(
            value=str(settings.skipped_details_limit)
        ),
        include_zip_var=make_bool_var(settings.include_snapshot_zip),
        redact_var=make_bool_var(settings.redact_sensitive_lines),
        include_hashes_var=make_bool_var(settings.include_hashes),
        include_line_counts_var=make_bool_var(settings.include_line_counts),
        include_tree_var=make_bool_var(settings.include_folder_tree),
        include_index_var=make_bool_var(settings.include_file_index),
        include_contents_var=make_bool_var(settings.include_file_contents),
        include_skipped_details_var=make_bool_var(
            settings.include_skipped_details
        ),
        timestamped_folder_var=make_bool_var(
            settings.timestamped_export_folder
        ),
        open_after_build_var=tk.BooleanVar(value=False),
        check_updates_startup_var=tk.BooleanVar(value=False),
        auto_install_var=tk.BooleanVar(value=False),
        status_text=tk.StringVar(
            value="Select a project folder."
        ),
    )
def profile_description(
    profile: str,
) -> str:
    """
    Return readable text explaining a profile.
    """
    if profile == PROFILE_STANDARD:
        return (
            "standard: quick everyday backup and project overview. "
            "Creates a ZIP snapshot, folder tree, and file index "
            "without hashes, line counts, full file contents, or "
            "skipped-file details."
        )
    if profile == PROFILE_ARCHIVE:
        return (
            "archive (default): maximum preservation mode. Includes "
            "all available export information with larger limits and "
            "enforced source completeness. Best for backups, long-term "
            "preservation, research archives, and full project records."
        )
    return "Unknown profile."
def apply_settings_to_state(
    state: GuiState,
    settings: ScanSettings,
) -> None:
    """
    Push ScanSettings values into GUI variables.
    User preference flags are intentionally not overwritten here:
    - open_after_build_var
    - check_updates_startup_var
    - auto_install_var
    """
    state.max_file_mb_var.set(
        bytes_to_mb_text(settings.max_file_bytes)
    )
    state.max_total_mb_var.set(
        bytes_to_mb_text(settings.max_total_bytes)
    )
    state.skipped_limit_var.set(
        str(settings.skipped_details_limit)
    )
    state.include_zip_var.set(settings.include_snapshot_zip)
    state.redact_var.set(settings.redact_sensitive_lines)
    state.include_hashes_var.set(settings.include_hashes)
    state.include_line_counts_var.set(settings.include_line_counts)
    state.include_tree_var.set(settings.include_folder_tree)
    state.include_index_var.set(settings.include_file_index)
    state.include_contents_var.set(settings.include_file_contents)
    state.include_skipped_details_var.set(
        settings.include_skipped_details
    )
    state.timestamped_folder_var.set(
        settings.timestamped_export_folder
    )
def apply_profile_defaults(
    state: GuiState,
) -> None:
    """
    Update visible option fields when profile changes.
    The GUI reads directly from constants.py through settings_for_profile().
    This removes duplicated per-profile values from the GUI layer.
    """
    settings = settings_for_profile(
        state.profile_var.get()
    )
    apply_settings_to_state(
        state,
        settings,
    )
def parse_mb_to_bytes(
    value: str,
    label: str,
) -> int:
    """
    Parse a GUI decimal MB value into bytes.
    """
    try:
        return int(float(value) * 1_000_000)
    except ValueError:
        raise ValueError(
            f"{label} must be numeric."
        )
def parse_nonnegative_int(
    value: str,
    label: str,
) -> int:
    """
    Parse a GUI whole-number field.
    """
    try:
        return max(0, int(value))
    except ValueError:
        raise ValueError(
            f"{label} must be a whole number."
        )
def build_settings_from_state(
    state: GuiState,
) -> ScanSettings:
    """
    Convert user-selected GUI values into ScanSettings.
    """
    settings = settings_for_profile(
        state.profile_var.get()
    )
    settings.output_dir_name = (
        state.output_dir_var.get().strip()
        or EXPORTS_DIRNAME
    )
    settings.include_snapshot_zip = state.include_zip_var.get()
    settings.redact_sensitive_lines = state.redact_var.get()
    settings.include_hashes = state.include_hashes_var.get()
    settings.include_line_counts = state.include_line_counts_var.get()
    settings.include_folder_tree = state.include_tree_var.get()
    settings.include_file_index = state.include_index_var.get()
    settings.include_file_contents = state.include_contents_var.get()
    settings.include_skipped_details = (
        state.include_skipped_details_var.get()
    )
    settings.timestamped_export_folder = (
        state.timestamped_folder_var.get()
    )
    settings.max_file_bytes = parse_mb_to_bytes(
        state.max_file_mb_var.get(),
        "Max File MB",
    )
    settings.max_total_bytes = parse_mb_to_bytes(
        state.max_total_mb_var.get(),
        "Max Total MB",
    )
    settings.skipped_details_limit = parse_nonnegative_int(
        state.skipped_limit_var.get(),
        "Skipped Details Limit",
    )
    return settings
def run_project_build(
    state: GuiState,
) -> BuildResult:
    """
    Run the actual project context build from GUI state.
    """
    folder = state.selected_folder.get().strip()
    if not folder:
        raise ValueError(
            "Please select a project folder first."
        )
    settings = build_settings_from_state(state)
    result = create_context(
        Path(folder),
        settings=settings,
    )
    state.last_export_dir = result.export_dir
    return result