from pathlib import Path
import os
import tkinter as tk
from tkinter import messagebox

from models import BuildResult


def open_folder(path: Path) -> None:
    """
    Open a folder in the operating system's file browser.

    os.startfile works on Windows.
    Other systems receive a readable message instead.
    """
    try:
        os.startfile(path)
    except AttributeError:
        messagebox.showinfo(
            "Open Folder",
            f"Export folder:\n{path}",
        )
    except Exception as exc:
        messagebox.showerror(
            "Open Folder Failed",
            str(exc),
        )


def show_error(
    title: str,
    message: str,
) -> None:
    """
    Show an error dialog.
    """
    messagebox.showerror(
        title,
        message,
    )


def show_warning(
    title: str,
    message: str,
) -> None:
    """
    Show a warning dialog.
    """
    messagebox.showwarning(
        title,
        message,
    )


def show_info(
    title: str,
    message: str,
) -> None:
    """
    Show an info dialog.
    """
    messagebox.showinfo(
        title,
        message,
    )


def ask_yes_no(
    title: str,
    message: str,
) -> bool:
    """
    Show a yes/no question dialog.
    """
    return messagebox.askyesno(
        title,
        message,
    )


def show_build_complete(
    result: BuildResult,
) -> None:
    """
    Show build completion details.
    """
    snapshot_line = ""

    if result.snapshot_path:
        snapshot_line = f"\n- {result.snapshot_path}"

    messagebox.showinfo(
        "Build Complete",
        (
            f"Export Folder:\n"
            f"{result.export_dir}\n\n"
            f"Included Files: {result.included_count}\n"
            f"Skipped Files: {result.skipped_count}"
            f"{snapshot_line}"
        ),
    )