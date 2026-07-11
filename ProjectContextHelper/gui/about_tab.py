import tkinter as tk

from constants import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    REPOSITORY_URL,
)


def create_about_tab(
    parent: tk.Frame,
) -> None:
    """
    Create the About tab.
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
            "Primary use cases:\n"
            "• AI-assisted development context\n"
            "• documentation snapshots\n"
            "• archival preservation\n"
            "• project handoff\n"
            "• source-code review bundles\n"
            "• timestamped local backups\n\n"
            f"Author: {AUTHOR}\n"
            f"Repository: {REPOSITORY_URL}"
        ),
    )

    about_text.pack(
        fill="both",
        expand=True,
        padx=18,
        pady=18,
    )