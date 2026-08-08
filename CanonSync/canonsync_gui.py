#!/usr/bin/env python3
"""
canonsync_gui.py
----------------
Tkinter GUI for CanonSync.

Point it at a parent folder (e.g. your GitHub directory). It discovers
every git repo inside, lets you choose which canonical files to sync
(.gitignore, .editorconfig, .gitattributes, LICENSE, ...), previews
exactly what would change per repo and per file, and writes on Apply.

- "block" files keep each repo's own rules around the managed block.
- "whole" files (LICENSE) are full replacements and are disabled by
  default in canon.config.json.

Pure standard library (tkinter). Local-first. Nothing is written until you
press Apply, and Apply asks for confirmation first.

Run:  python canonsync_gui.py
"""
from __future__ import annotations

from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import canon_core as core

DEFAULT_CONFIG = "canon.config.json"

STATUS_LABEL = {
    core.STATUS_CREATE: "CREATE",
    core.STATUS_UPDATE: "UPDATE",
    core.STATUS_UNCHANGED: "unchanged",
    core.STATUS_MISSING: "MISSING",
    core.STATUS_SKIPPED: "skipped",
}
STATUS_COLOR = {
    core.STATUS_CREATE: "#0a7d28",
    core.STATUS_UPDATE: "#b35c00",
    core.STATUS_UNCHANGED: "#666666",
    core.STATUS_MISSING: "#b00020",
    core.STATUS_SKIPPED: "#666666",
}


class CanonSyncApp(tk.Tk):
    """
    Main application window.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{core.APP_NAME} v{core.APP_VERSION}")
        self.geometry("900x620")
        self.minsize(760, 520)

        self.config_path = tk.StringVar(value=str(Path(DEFAULT_CONFIG).resolve()))
        self.parent_dir = tk.StringVar(value="")
        self.repos: list[Path] = []
        self.last_results: list[dict] = []
        self.item_vars: dict[str, tk.BooleanVar] = {}
        self.config_data: dict = {}

        self._build_widgets()
        self._load_config_items()

    # -- layout -----------------------------------------------------------
    def _build_widgets(self) -> None:
        pad = {"padx": 8, "pady": 4}

        cfg = ttk.LabelFrame(self, text="Canon config")
        cfg.pack(fill="x", **pad)
        ttk.Entry(cfg, textvariable=self.config_path).pack(
            side="left", fill="x", expand=True, padx=6, pady=6
        )
        ttk.Button(cfg, text="Browse…", command=self._pick_config).pack(side="left", padx=3, pady=6)
        ttk.Button(cfg, text="Reload", command=self._load_config_items).pack(side="left", padx=3, pady=6)

        self.items_frame = ttk.LabelFrame(self, text="Canonical files to sync")
        self.items_frame.pack(fill="x", **pad)

        mid = ttk.LabelFrame(self, text="Repositories folder")
        mid.pack(fill="x", **pad)
        ttk.Entry(mid, textvariable=self.parent_dir).pack(
            side="left", fill="x", expand=True, padx=6, pady=6
        )
        ttk.Button(mid, text="Browse…", command=self._pick_parent).pack(side="left", padx=3, pady=6)
        ttk.Button(mid, text="Scan", command=self._scan).pack(side="left", padx=3, pady=6)

        table = ttk.LabelFrame(self, text="Plan")
        table.pack(fill="both", expand=True, **pad)
        columns = ("status", "item", "repo")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", height=12)
        self.tree.heading("status", text="Action")
        self.tree.heading("item", text="File")
        self.tree.heading("repo", text="Repository")
        self.tree.column("status", width=100, anchor="w", stretch=False)
        self.tree.column("item", width=130, anchor="w", stretch=False)
        self.tree.column("repo", width=620, anchor="w")
        for status, color in STATUS_COLOR.items():
            self.tree.tag_configure(status, foreground=color)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scroll.pack(side="left", fill="y", pady=6)
        self.tree.configure(yscrollcommand=scroll.set)

        actions = ttk.Frame(self)
        actions.pack(fill="x", **pad)
        ttk.Button(actions, text="Preview (dry run)", command=self._preview).pack(side="left", padx=6)
        self.apply_btn = ttk.Button(actions, text="Apply", command=self._apply, state="disabled")
        self.apply_btn.pack(side="left", padx=6)
        ttk.Button(actions, text="Quit", command=self.destroy).pack(side="right", padx=6)

        self.status_var = tk.StringVar(value="Load a config, pick a repos folder, then Scan.")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

    # -- config / items ---------------------------------------------------
    def _pick_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Select canon.config.json", initialfile=DEFAULT_CONFIG
        )
        if path:
            self.config_path.set(path)
            self._load_config_items()

    def _load_config_items(self) -> None:
        for child in self.items_frame.winfo_children():
            child.destroy()
        self.item_vars.clear()
        cfg_path = Path(self.config_path.get()).expanduser().resolve()
        try:
            self.config_data = core.load_config(cfg_path)
        except Exception as exc:
            messagebox.showerror(core.APP_NAME, f"Could not load config:\n{exc}")
            return
        for item in self.config_data.get("items", []):
            var = tk.BooleanVar(value=bool(item.get("enabled", True)))
            self.item_vars[item["name"]] = var
            text = f"{item['name']}  →  {item['dest']}  [{item.get('mode', 'block')}]"
            ttk.Checkbutton(self.items_frame, text=text, variable=var).pack(
                anchor="w", padx=8, pady=1
            )
        self.status_var.set(
            f"Loaded {len(self.item_vars)} canonical file(s). Pick a repos folder and Scan."
        )

    def _selected_items(self) -> set[str]:
        return {name for name, var in self.item_vars.items() if var.get()}

    # -- helpers ----------------------------------------------------------
    def _pick_parent(self) -> None:
        path = filedialog.askdirectory(title="Select the folder containing your repos")
        if path:
            self.parent_dir.set(path)

    def _clear_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)

    def _fill_table(self, results: list[dict]) -> None:
        self._clear_table()
        for r in results:
            status = r["status"]
            self.tree.insert(
                "",
                "end",
                values=(STATUS_LABEL[status], r["item"], str(r["repo"])),
                tags=(status,),
            )

    def _scan(self) -> None:
        parent = self.parent_dir.get().strip()
        if not parent:
            messagebox.showwarning(core.APP_NAME, "Choose a repositories folder first.")
            return
        root = Path(parent).expanduser().resolve()
        if not root.exists():
            messagebox.showerror(core.APP_NAME, f"Folder does not exist:\n{root}")
            return
        self.repos = core.discover_repos(root)
        self._clear_table()
        self.apply_btn.configure(state="disabled")
        if not self.repos:
            self.status_var.set("No git repos found in that folder.")
            messagebox.showinfo(core.APP_NAME, "No git repositories found (no .git in immediate subfolders).")
            return
        for repo in self.repos:
            self.tree.insert("", "end", values=("(scan)", "", str(repo)))
        self.status_var.set(f"Found {len(self.repos)} repo(s). Press Preview.")

    def _run(self, apply: bool) -> None:
        if not self.repos:
            messagebox.showwarning(core.APP_NAME, "Scan for repos first.")
            return
        only = self._selected_items()
        if not only:
            messagebox.showwarning(core.APP_NAME, "Select at least one canonical file to sync.")
            return
        try:
            results = core.sync(self.config_data, self.repos, apply=apply, only=only)
        except Exception as exc:
            messagebox.showerror(core.APP_NAME, f"Sync failed:\n{exc}")
            return
        self.last_results = results
        self._fill_table(results)
        c = core.summarize(results)
        verb = "Wrote" if apply else "Would change"
        self.status_var.set(
            f"{verb}: {c[core.STATUS_CREATE]} create, {c[core.STATUS_UPDATE]} update, "
            f"{c[core.STATUS_UNCHANGED]} unchanged, {c[core.STATUS_MISSING]} missing."
        )
        has_changes = (c[core.STATUS_CREATE] + c[core.STATUS_UPDATE]) > 0
        self.apply_btn.configure(state=("normal" if (has_changes and not apply) else "disabled"))
        if apply:
            messagebox.showinfo(core.APP_NAME, "Done. Changes written.")

    def _preview(self) -> None:
        self._run(apply=False)

    def _apply(self) -> None:
        c = core.summarize(self.last_results) if self.last_results else None
        if not c or (c[core.STATUS_CREATE] + c[core.STATUS_UPDATE]) == 0:
            messagebox.showinfo(core.APP_NAME, "Nothing to apply. Preview first.")
            return
        whole_selected = [
            i["name"]
            for i in core.enabled_items(self.config_data, only=self._selected_items())
            if i.get("mode") == core.MODE_WHOLE
        ]
        warn = ""
        if whole_selected:
            warn = (
                f"\n\nNOTE: {', '.join(whole_selected)} use WHOLE mode and will "
                "REPLACE the entire destination file in each repo."
            )
        if not messagebox.askyesno(
            core.APP_NAME,
            f"Write {(c[core.STATUS_CREATE] + c[core.STATUS_UPDATE])} change(s) "
            f"across the selected repos?{warn}",
        ):
            return
        self._run(apply=True)


def main() -> None:
    CanonSyncApp().mainloop()


if __name__ == "__main__":
    main()
