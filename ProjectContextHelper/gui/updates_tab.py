import tkinter as tk

from constants import RELEASES_URL

from gui.builders import GuiState

from gui.dialogs import (
    ask_yes_no,
    show_info,
)

from updater import (
    check_for_updates,
    open_releases_page,
)


def create_updates_tab(
    parent: tk.Frame,
    window: tk.Tk,
    state: GuiState,
):
    """
    Create the Updates tab.

    Returns the update-check function so main_gui.py can call it
    during startup when the startup checkbox is enabled.
    """

    update_frame = tk.LabelFrame(
        parent,
        text="Update Checker",
        padx=12,
        pady=12,
    )

    update_frame.pack(
        fill="x",
        padx=16,
        pady=(16, 8),
    )

    update_status = tk.StringVar(
        value=(
            "Check GitHub Releases for a newer version. "
            "No update is installed silently."
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

    def run_update_check_gui(
        show_up_to_date: bool = True,
    ) -> None:

        update_status.set("Checking for updates...")
        window.update_idletasks()

        info = check_for_updates()

        update_status.set(info.message)

        if info.update_available:
            answer = ask_yes_no(
                "Update Available",
                (
                    f"{info.message}\n\n"
                    "Open the GitHub Releases page?"
                ),
            )

            if answer:
                open_releases_page(info.release_url)

        elif show_up_to_date:
            show_info(
                "Update Check",
                info.message,
            )

    update_button = tk.Button(
        update_frame,
        text="Check for Updates",
        command=run_update_check_gui,
        height=2,
        font=("Segoe UI", 11, "bold"),
    )

    update_button.pack(
        anchor="w",
        pady=(0, 8),
    )

    startup_check = tk.Checkbutton(
        update_frame,
        text="Check for updates when the app opens",
        variable=state.check_updates_startup_var,
    )

    startup_check.pack(
        anchor="w",
    )

    releases_button = tk.Button(
        update_frame,
        text="Open Releases Page",
        command=lambda: open_releases_page(RELEASES_URL),
    )

    releases_button.pack(
        anchor="w",
        pady=(8, 0),
    )

    return run_update_check_gui