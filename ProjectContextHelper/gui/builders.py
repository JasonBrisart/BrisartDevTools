from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk

from constants import settings_for_profile
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

    status_text: tk.StringVar
    last_export_dir: Path | None = None


def make_gui_state() -> GuiState:
    """
    Create the default GUI state.
    """
    return GuiState(
        selected_folder=tk.StringVar(value=""),
        profile_var=tk.StringVar(value="standard"),
        output_dir_var=tk.StringVar(value="PROJECT_CONTEXT_EXPORTS"),

        max_file_mb_var=tk.StringVar(value="0.35"),
        max_total_mb_var=tk.StringVar(value="5"),
        skipped_limit_var=tk.StringVar(value="250"),

        include_zip_var=tk.BooleanVar(value=True),
        redact_var=tk.BooleanVar(value=True),
        include_hashes_var=tk.BooleanVar(value=True),
        include_line_counts_var=tk.BooleanVar(value=True),
        include_tree_var=tk.BooleanVar(value=True),
        include_index_var=tk.BooleanVar(value=True),
        include_contents_var=tk.BooleanVar(value=True),
        include_skipped_details_var=tk.BooleanVar(value=True),
        timestamped_folder_var=tk.BooleanVar(value=True),
        open_after_build_var=tk.BooleanVar(value=False),
        check_updates_startup_var=tk.BooleanVar(value=False),

        status_text=tk.StringVar(value="Select a project folder."),
    )


def profile_description(profile: str) -> str:
    """
    Return readable text explaining a profile.
    """
    if profile == "standard":
        return (
            "standard: clean default export for everyday project context. "
            "Best for AI review, documentation, and quick code snapshots."
        )

    if profile == "expanded":
        return (
            "expanded: includes more support files like logs, templates, "
            "samples, lock files, and documentation extras. Best when you "
            "want fuller development context."
        )

    if profile == "archive":
        return (
            "archive: broadest source-oriented profile with more programming "
            "languages and larger limits. Best for preservation, handoff, "
            "and fuller project snapshots."
        )

    return "Unknown profile."


def apply_profile_defaults(
    state: GuiState,
) -> None:
    """
    Update visible size-limit fields when profile changes.
    """
    profile = state.profile_var.get()

    if profile == "standard":
        state.max_file_mb_var.set("0.35")
        state.max_total_mb_var.set("5")

    elif profile == "expanded":
        state.max_file_mb_var.set("0.5")
        state.max_total_mb_var.set("10")

    elif profile == "archive":
        state.max_file_mb_var.set("1")
        state.max_total_mb_var.set("25")


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
        or "PROJECT_CONTEXT_EXPORTS"
    )

    settings.include_snapshot_zip = state.include_zip_var.get()
    settings.redact_sensitive_lines = state.redact_var.get()
    settings.include_hashes = state.include_hashes_var.get()
    settings.include_line_counts = state.include_line_counts_var.get()
    settings.include_folder_tree = state.include_tree_var.get()
    settings.include_file_index = state.include_index_var.get()
    settings.include_file_contents = state.include_contents_var.get()
    settings.include_skipped_details = state.include_skipped_details_var.get()
    settings.timestamped_export_folder = state.timestamped_folder_var.get()

    try:
        settings.max_file_bytes = int(
            float(state.max_file_mb_var.get())
            * 1_000_000
        )
    except ValueError:
        raise ValueError(
            "Max File MB must be numeric."
        )

    try:
        settings.max_total_bytes = int(
            float(state.max_total_mb_var.get())
            * 1_000_000
        )
    except ValueError:
        raise ValueError(
            "Max Total MB must be numeric."
        )

    try:
        settings.skipped_details_limit = max(
            0,
            int(state.skipped_limit_var.get()),
        )
    except ValueError:
        raise ValueError(
            "Skipped Details Limit must be a whole number."
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