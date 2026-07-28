import tkinter as tk

from changelog import (
    build_changelog_text,
    write_changelog_markdown,
)
from constants import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    REPOSITORY_URL,
)
from gui.builders import GuiState
from gui.dialogs import (
    show_error,
    show_info,
)
from updater import (
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

    Shows application information, the full changelog (read from the
    separate changelog module), and a single updates control: an
    automatic check-and-download on startup.

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

    changelog_frame = tk.LabelFrame(
        parent,
        text="Changelog",
        padx=8,
        pady=8,
    )
    changelog_frame.pack(
        fill="both",
        expand=True,
        padx=16,
        pady=(8, 8),
    )

    text_container = tk.Frame(changelog_frame)
    text_container.pack(
        fill="both",
        expand=True,
    )

    scrollbar = tk.Scrollbar(text_container)
    scrollbar.pack(
        side="right",
        fill="y",
    )

    changelog_text = tk.Text(
        text_container,
        wrap="word",
        height=12,
        yscrollcommand=scrollbar.set,
        relief="flat",
        padx=8,
        pady=6,
    )
    changelog_text.pack(
        side="left",
        fill="both",
        expand=True,
    )
    scrollbar.config(command=changelog_text.yview)

    changelog_text.insert("1.0", build_changelog_text())
    changelog_text.config(state="disabled")

    def export_changelog_md() -> None:
        try:
            path = write_changelog_markdown(
                application_dir() / "CHANGELOG.md"
            )
        except Exception as exc:
            show_error(
                "Changelog Export Failed",
                str(exc),
            )
            return
        show_info(
            "Changelog Exported",
            f"CHANGELOG.md written to:\n{path}",
        )

    changelog_buttons = tk.Frame(changelog_frame)
    changelog_buttons.pack(
        fill="x",
        pady=(8, 0),
    )

    export_md_button = tk.Button(
        changelog_buttons,
        text="Export CHANGELOG.md",
        command=export_changelog_md,
    )
    export_md_button.pack(
        side="left",
    )

    releases_button = tk.Button(
        changelog_buttons,
        text="Open Releases Page",
        command=lambda: open_releases_page(),
    )
    releases_button.pack(
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
            "When enabled, updates are checked and downloaded "
            "automatically on startup. Downloaded updates are staged "
            "in the 'updates' folder and are not applied automatically."
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
            dest = download_update(info)
        except Exception as exc:
            update_status.set(f"Update download failed: {exc}")
            return

        update_status.set(
            f"Update {info.latest_version} downloaded to:\n{dest}"
        )
        show_info(
            "Update Downloaded",
            (
                f"Version {info.latest_version} was downloaded and staged in:\n"
                f"{dest}\n\n"
                "Review the staged files and restart to apply."
            ),
        )

    def startup_update_check() -> None:
        if state.check_updates_startup_var.get():
            perform_auto_update()

    return startup_update_check
