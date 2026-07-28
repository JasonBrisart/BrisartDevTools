import tkinter as tk
from tkinter import ttk

from constants import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    REPOSITORY_URL,
)
from gui.builders import make_gui_state
from gui.build_tab import create_build_tab
from gui.options_tab import create_options_tab
from gui.about_tab import create_about_tab


def run_gui() -> None:
    """
    Launch the Project Context Helper GUI.

    This file intentionally stays small.
    Individual tabs live in their own modules.

    The former Updates tab has been merged into the About tab, which
    also performs the automatic startup update check.
    """
    window = tk.Tk()
    window.title(f"{APP_NAME} v{APP_VERSION}")
    window.geometry("860x760")
    window.minsize(780, 680)

    state = make_gui_state()

    header = tk.Label(
        window,
        text=APP_NAME,
        font=("Segoe UI", 20, "bold"),
    )
    header.pack(
        pady=(18, 4),
    )

    subheader = tk.Label(
        window,
        text=(
            f"v{APP_VERSION} \u2022 "
            f"{AUTHOR} \u2022 "
            f"{REPOSITORY_URL}"
        ),
        font=("Segoe UI", 9),
        fg="#555555",
    )
    subheader.pack(
        pady=(0, 12),
    )

    notebook = ttk.Notebook(window)
    notebook.pack(
        fill="both",
        expand=True,
        padx=24,
        pady=(0, 8),
    )

    build_tab = tk.Frame(notebook)
    options_tab = tk.Frame(notebook)
    about_tab = tk.Frame(notebook)

    notebook.add(
        build_tab,
        text="Build",
    )
    notebook.add(
        options_tab,
        text="Options",
    )
    notebook.add(
        about_tab,
        text="About",
    )

    create_build_tab(
        parent=build_tab,
        window=window,
        state=state,
    )
    create_options_tab(
        parent=options_tab,
        state=state,
    )
    startup_update_check = create_about_tab(
        parent=about_tab,
        window=window,
        state=state,
    )

    status_bar = tk.Label(
        window,
        textvariable=state.status_text,
        anchor="w",
        relief="sunken",
        padx=8,
    )
    status_bar.pack(
        side="bottom",
        fill="x",
    )

    window.after(
        500,
        startup_update_check,
    )

    window.mainloop()


if __name__ == "__main__":
    run_gui()