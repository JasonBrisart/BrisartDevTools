from pathlib import Path
import tkinter as tk
from tkinter import ttk
from constants import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    REPOSITORY_URL,
)
from gui.builders import GuiState
from gui.dialogs import (
    ask_yes_no,
    open_folder,
    show_error,
    show_info,
)
from history import (
    HistoryEntry,
    clear_history,
    recent_entries,
)
from updater import (
    apply_staged_update,
    application_dir,
    check_for_updates,
    download_update,
    open_releases_page,
)
def create_about_tab(
    parent: tk.Frame,
    window: tk.Tk,
    state: GuiState,
):
    """
    Create the combined About tab.
    Shows application information, a Recent Exports panel built from
    local build history, and the update controls (staged download,
    plus an opt-in toggle to apply staged updates in place).
    Returns the startup update function so main_gui.py can run it
    shortly after the window opens.
    """
    about_text = tk.Label(
        parent,
        justify="left",
        anchor="nw",
        wraplength=760,
        text=(
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "A no-dependency utility that packages a project folder into a "
            "readable Markdown context file, JSON manifest, summary file, "
            "settings record, and optional ZIP snapshot.\n\n"
            f"Author: {AUTHOR}\n"
            f"Repository: {REPOSITORY_URL}"
        ),
    )
    about_text.pack(
        fill="x",
        padx=18,
        pady=(18, 8),
    )
    releases_button = tk.Button(
        parent,
        text="Open Releases Page",
        command=lambda: open_releases_page(),
    )
    releases_button.pack(
        anchor="w",
        padx=18,
        pady=(0, 8),
    )
    history_frame = tk.LabelFrame(
        parent,
        text="Recent Exports",
        padx=8,
        pady=8,
    )
    history_frame.pack(
        fill="both",
        expand=True,
        padx=16,
        pady=(8, 8),
    )
    tree_container = tk.Frame(history_frame)
    tree_container.pack(
        fill="both",
        expand=True,
    )
    history_scrollbar = tk.Scrollbar(tree_container)
    history_scrollbar.pack(
        side="right",
        fill="y",
    )
    columns = (
        "created",
        "profile",
        "included",
        "skipped",
        "root",
    )
    history_tree = ttk.Treeview(
        tree_container,
        columns=columns,
        show="headings",
        height=9,
        yscrollcommand=history_scrollbar.set,
    )
    history_tree.heading("created", text="Created")
    history_tree.heading("profile", text="Profile")
    history_tree.heading("included", text="Included")
    history_tree.heading("skipped", text="Skipped")
    history_tree.heading("root", text="Project Folder")
    history_tree.column("created", width=150, anchor="w")
    history_tree.column("profile", width=70, anchor="center")
    history_tree.column("included", width=70, anchor="center")
    history_tree.column("skipped", width=70, anchor="center")
    history_tree.column("root", width=280, anchor="w")
    history_tree.pack(
        side="left",
        fill="both",
        expand=True,
    )
    history_scrollbar.config(command=history_tree.yview)
    entry_lookup: dict[str, HistoryEntry] = {}
    def refresh_history() -> None:
        history_tree.delete(*history_tree.get_children())
        entry_lookup.clear()
        entries = recent_entries(
            limit=20,
            app_dir=application_dir(),
        )
        if not entries:
            history_tree.insert(
                "",
                "end",
                values=(
                    "No exports yet.",
                    "",
                    "",
                    "",
                    "Build a project context export to see it here.",
                ),
            )
            return
        for entry in entries:
            item_id = history_tree.insert(
                "",
                "end",
                values=(
                    entry.created,
                    entry.profile,
                    entry.included_count,
                    entry.skipped_count,
                    entry.root,
                ),
            )
            entry_lookup[item_id] = entry
    refresh_history()
    def open_selected_export() -> None:
        selection = history_tree.selection()
        if not selection:
            show_info(
                "No Selection",
                "Select a recent export first.",
            )
            return
        entry = entry_lookup.get(selection[0])
        if entry is None:
            return
        export_dir = Path(entry.export_dir)
        if not export_dir.exists():
            show_error(
                "Folder Not Found",
                f"This export folder no longer exists:\n{export_dir}",
            )
            return
        open_folder(export_dir)
    def clear_export_history() -> None:
        if not ask_yes_no(
            "Clear History",
            (
                "Remove all recorded export history?\n\n"
                "This only clears this list. It does not delete any "
                "actual export files or folders."
            ),
        ):
            return
        clear_history(app_dir=application_dir())
        refresh_history()
    history_buttons = tk.Frame(history_frame)
    history_buttons.pack(
        fill="x",
        pady=(8, 0),
    )
    open_export_button = tk.Button(
        history_buttons,
        text="Open Selected Export Folder",
        command=open_selected_export,
    )
    open_export_button.pack(
        side="left",
    )
    refresh_button = tk.Button(
        history_buttons,
        text="Refresh",
        command=refresh_history,
    )
    refresh_button.pack(
        side="left",
        padx=(8, 0),
    )
    clear_button = tk.Button(
        history_buttons,
        text="Clear History",
        command=clear_export_history,
    )
    clear_button.pack(
        side="left",
        padx=(8, 0),
    )
    update_frame = tk.LabelFrame(
        parent,
        text="Updates",
        padx=12,
        pady=12,
    )
    update_frame.pack(
        fill="x",
        padx=16,
        pady=(8, 8),
    )
    update_status = tk.StringVar(
        value=(
            "When 'check on startup' is enabled, updates are checked and "
            "downloaded automatically. By default, downloaded updates are "
            "only staged in the 'updates' folder and are not applied. "
            "Enable 'automatically install' below to have staged updates "
            "overwrite the running application's own files instead."
        )
    )
    update_label = tk.Label(
        update_frame,
        textvariable=update_status,
        justify="left",
        anchor="w",
        wraplength=720,
    )
    update_label.pack(
        fill="x",
        pady=(0, 10),
    )
    startup_check = tk.Checkbutton(
        update_frame,
        text="Automatically check for and download updates on startup",
        variable=state.check_updates_startup_var,
    )
    startup_check.pack(
        anchor="w",
    )
    auto_install_check = tk.Checkbutton(
        update_frame,
        text=(
            "Automatically install downloaded updates "
            "(overwrites current files after a backup)"
        ),
        variable=state.auto_install_var,
    )
    auto_install_check.pack(
        anchor="w",
        pady=(4, 0),
    )
    def perform_auto_update() -> None:
        update_status.set("Checking for updates...")
        window.update_idletasks()
        info = check_for_updates()
        if not info.update_available:
            update_status.set(info.message)
            return
        update_status.set(
            f"Update available: {info.latest_version}. Downloading..."
        )
        window.update_idletasks()
        try:
            staged_dir = download_update(info)
        except Exception as exc:
            update_status.set(f"Update download failed: {exc}")
            return
        if not state.auto_install_var.get():
            update_status.set(
                f"Update {info.latest_version} downloaded to:\n{staged_dir}"
            )
            show_info(
                "Update Downloaded",
                (
                    f"Version {info.latest_version} was downloaded and "
                    f"staged in:\n{staged_dir}\n\n"
                    "Review the staged files and restart to apply, or "
                    "enable 'Automatically install downloaded updates' so "
                    "future updates are applied without a manual step."
                ),
            )
            return
        update_status.set(
            f"Installing update {info.latest_version}..."
        )
        window.update_idletasks()
        try:
            result = apply_staged_update(staged_dir)
        except Exception as exc:
            update_status.set(f"Update install failed: {exc}")
            show_error(
                "Update Install Failed",
                (
                    f"{exc}\n\n"
                    "The application's previous files, if a backup was "
                    "completed before the failure, can be found under:\n"
                    f"{application_dir() / 'updates' / 'backups'}"
                ),
            )
            return
        update_status.set(
            f"Update {info.latest_version} installed. Restart to finish."
        )
        show_info(
            "Update Installed",
            (
                f"Version {info.latest_version} was installed over the "
                "current application files.\n\n"
                f"Backup of the previous version:\n{result.backup_dir}\n\n"
                f"Files updated: {len(result.applied_files)}\n\n"
                "Restart the application to run the new version."
            ),
        )
    def startup_update_check() -> None:
        if state.check_updates_startup_var.get():
            perform_auto_update()
    return startup_update_check
