from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import datetime
import hashlib
import io
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
import zipfile

from constants import (
    APP_NAME,
    APP_VERSION,
    EXPORTS_DIRNAME,
    RELEASE_TAG_PREFIX,
    RELEASES_LIST_URL,
    RELEASES_URL,
    STAGED_EXE_FILENAME,
)

UPDATES_DIRNAME = "updates"
BACKUPS_DIRNAME = "backups"

PROTECTED_NAMES = {
    UPDATES_DIRNAME,
    EXPORTS_DIRNAME,
    "__pycache__",
    ".git",
    "download.zip",
}


def is_frozen() -> bool:
    """
    Return True when running as a PyInstaller-built executable.

    PyInstaller sets sys.frozen = True at runtime in a built exe. This
    is used throughout this module to decide between two entirely
    different update mechanisms: swapping the compiled .exe itself
    (frozen) versus overwriting .py source files in place (script /
    development mode).
    """
    return bool(getattr(sys, "frozen", False))


def application_dir() -> Path:
    """
    Return the directory that should be treated as this application's
    own persistent folder, for settings, history, and update purposes.

    When running as a normal Python script, this is the folder
    containing this module (__file__). When running as a frozen
    PyInstaller executable — especially a --onefile build — __file__
    instead resolves to a temporary extraction folder (sys._MEIPASS)
    that PyInstaller deletes the moment the process exits. Anything
    written there (settings, history, update backups) would silently
    vanish on every run. In frozen mode this returns the folder that
    actually contains the running .exe file instead, which persists
    across launches.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


@dataclass(slots=True)
class UpdateInfo:
    """
    Result of an update check.

    asset_kind is "exe" when a compiled .exe release asset was found
    and selected (used when running as a frozen executable), "zip"
    when a packaged .zip asset was selected (used in script/development
    mode), or "none" when a newer release exists but no asset
    compatible with the current run mode was found.

    asset_digest holds the asset's published checksum, formatted as
    GitHub provides it (e.g. "sha256:<hex>"), when available. Empty
    string if no digest was published for this asset.
    """
    update_available: bool
    current_version: str
    latest_version: str
    message: str
    release_url: str
    download_url: str = ""
    asset_kind: str = "zip"
    asset_digest: str = ""


@dataclass(slots=True)
class InstallResult:
    """
    Result of applying a staged source-file update in place.
    Only used for the script/dev-mode (non-frozen) update path.
    """
    backup_dir: Path
    staged_dir: Path
    applied_files: tuple[Path, ...]
    restart_required: bool = True


def normalize_version(value: str) -> tuple[int, ...]:
    """
    Convert version strings such as:
    2.0.0
    v2.1.5
    project-context-helper-v2.2.0
    into a comparable tuple.
    """
    cleaned = ""
    for char in value:
        if char.isdigit() or char == ".":
            cleaned += char
    parts = [
        int(part)
        for part in cleaned.split(".")
        if part.strip().isdigit()
    ]
    if not parts:
        return (0,)
    return tuple(parts)


def is_newer_version(
    latest: str,
    current: str,
) -> bool:
    return normalize_version(latest) > normalize_version(current)


def version_slug(value: str) -> str:
    slug = "".join(
        char
        for char in value
        if char.isalnum() or char in {".", "-", "_"}
    )
    return slug or "latest"


def find_latest_release_payload(
    releases: list[dict],
    tag_prefix: str,
) -> dict | None:
    """
    Return the first release in a /releases list whose tag matches
    this tool's tag prefix.

    BrisartDevTools is a monorepo: the list returned by GitHub is
    sorted newest-first across ALL tools in the repo, so the first
    entry overall is not necessarily a Project Context Helper release.
    This filters to the first entry whose tag_name actually starts
    with RELEASE_TAG_PREFIX, which is the true "latest" release for
    this tool specifically.
    """
    for release in releases:
        tag_name = release.get("tag_name") or ""
        if tag_name.startswith(tag_prefix):
            return release
    return None


def resolve_asset(
    payload: dict,
) -> tuple[str, str, str]:
    """
    Pick the best downloadable asset from a release payload.

    Returns (download_url, kind, digest):
      kind is "exe" when a compiled .exe asset was selected, "zip"
      when a packaged .zip asset was selected, or "none" when no
      asset compatible with the current run mode was attached to the
      release. digest is the asset's published checksum string
      (e.g. "sha256:<hex>") if GitHub provided one, else "".

    When running as a frozen executable, only an attached .exe asset
    is considered: a compiled exe cannot apply a source-file update to
    itself. In script/dev mode, only an attached packaged .zip asset
    is considered.

    This never falls back to GitHub's auto-generated source
    zipball_url/tarball_url. BrisartDevTools is a monorepo, so that
    archive contains the source of every tool in the repository, not
    just this one — using it as a fallback would silently download
    and (if applied) extract the entire repository instead of just
    this program's release asset.
    """
    assets = payload.get("assets") or []
    if is_frozen():
        for asset in assets:
            name = (asset.get("name") or "").lower()
            if name.endswith(".exe"):
                return (
                    asset.get("browser_download_url") or "",
                    "exe",
                    asset.get("digest") or "",
                )
        return "", "none", ""
    for asset in assets:
        name = (asset.get("name") or "").lower()
        if name.endswith(".zip"):
            return (
                asset.get("browser_download_url") or "",
                "zip",
                asset.get("digest") or "",
            )
    return "", "none", ""


def check_for_updates(
    timeout_seconds: int = 6,
) -> UpdateInfo:
    """
    Check GitHub Releases for the newest Project Context Helper
    release.

    Fetches the full releases list for the BrisartDevTools monorepo
    and filters by RELEASE_TAG_PREFIX, rather than using GitHub's
    /releases/latest endpoint, which returns the newest release for
    the entire repository regardless of which tool it belongs to.

    If a newer release exists but resolve_asset() cannot find an
    asset compatible with the current run mode, update_available is
    still True (so the UI can tell the user a release exists) but
    asset_kind is "none" and download_url is empty, so nothing is
    ever downloaded in that case.
    """
    try:
        request = urllib.request.Request(
            RELEASES_LIST_URL,
            headers={"User-Agent": APP_NAME.replace(" ", "")},
        )
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            releases = json.loads(response.read().decode("utf-8"))
        payload = find_latest_release_payload(
            releases,
            RELEASE_TAG_PREFIX,
        )
        if payload is None:
            return UpdateInfo(
                update_available=False,
                current_version=APP_VERSION,
                latest_version=APP_VERSION,
                message=(
                    "No Project Context Helper release was found "
                    "in the BrisartDevTools releases list."
                ),
                release_url=RELEASES_URL,
            )
        latest_version = (
            payload.get("tag_name")
            or payload.get("name")
            or APP_VERSION
        )
        release_url = payload.get("html_url") or RELEASES_URL
        download_url, asset_kind, asset_digest = resolve_asset(payload)
        if not is_newer_version(latest_version, APP_VERSION):
            return UpdateInfo(
                update_available=False,
                current_version=APP_VERSION,
                latest_version=latest_version,
                message=f"You are running the latest version ({APP_VERSION}).",
                release_url=release_url,
                download_url=download_url,
                asset_kind=asset_kind,
                asset_digest=asset_digest,
            )
        if asset_kind == "none":
            mode_note = (
                "this build is a compiled executable, so it can only "
                "apply a .exe release asset"
                if is_frozen()
                else "this is running in script/dev mode, so it can "
                "only apply a packaged .zip release asset"
            )
            return UpdateInfo(
                update_available=True,
                current_version=APP_VERSION,
                latest_version=latest_version,
                message=(
                    f"Update available: {latest_version} "
                    f"(current: {APP_VERSION}), but no compatible "
                    f"download was found for this run mode — {mode_note}."
                ),
                release_url=release_url,
                download_url="",
                asset_kind="none",
                asset_digest="",
            )
        return UpdateInfo(
            update_available=True,
            current_version=APP_VERSION,
            latest_version=latest_version,
            message=(
                f"Update available: {latest_version} "
                f"(current: {APP_VERSION})"
            ),
            release_url=release_url,
            download_url=download_url,
            asset_kind=asset_kind,
            asset_digest=asset_digest,
        )
    except urllib.error.URLError as exc:
        return UpdateInfo(
            update_available=False,
            current_version=APP_VERSION,
            latest_version=APP_VERSION,
            message=f"Update check failed: {exc}",
            release_url=RELEASES_URL,
        )
    except Exception as exc:
        return UpdateInfo(
            update_available=False,
            current_version=APP_VERSION,
            latest_version=APP_VERSION,
            message=f"Update check failed: {exc}",
            release_url=RELEASES_URL,
        )


def verify_digest(
    data: bytes,
    digest: str,
) -> None:
    """
    Verify downloaded bytes against a GitHub asset digest string, such
    as "sha256:<hex>". Raises ValueError on mismatch. Silently returns
    if no digest was published (nothing to verify against), or if the
    digest is in an unrecognized format.
    """
    if not digest or ":" not in digest:
        return
    algorithm, _, expected = digest.partition(":")
    algorithm = algorithm.lower().strip()
    expected = expected.lower().strip()
    if algorithm != "sha256":
        return
    actual = hashlib.sha256(data).hexdigest().lower()
    if actual != expected:
        raise ValueError(
            "Downloaded update failed checksum verification. "
            f"Expected {expected}, got {actual}."
        )


# ============================================================
# Script / dev-mode update path (overwrites .py source files)
# ============================================================

def download_update(
    info: UpdateInfo,
    dest_dir: Path | None = None,
    timeout_seconds: int = 60,
) -> Path:
    """
    Download and extract a .zip release update into a staging folder.

    Only used for asset_kind == "zip" (script/dev mode). For
    asset_kind == "exe", use stage_exe_update() instead. Callers must
    never invoke this when asset_kind == "none" — there is no
    download_url in that case.
    """
    if not info.download_url:
        raise ValueError("No download URL is available for this release.")
    if dest_dir is None:
        dest_dir = (
            application_dir()
            / UPDATES_DIRNAME
            / f"v{version_slug(info.latest_version)}"
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        info.download_url,
        headers={"User-Agent": APP_NAME.replace(" ", "")},
    )
    with urllib.request.urlopen(
        request,
        timeout=timeout_seconds,
    ) as response:
        data = response.read()
    if info.asset_digest:
        verify_digest(data, info.asset_digest)
    archive_path = dest_dir / "download.zip"
    archive_path.write_bytes(data)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            archive.extractall(dest_dir)
    except zipfile.BadZipFile:
        pass
    return dest_dir


def find_release_root(extract_dir: Path) -> Path:
    """
    Locate the actual package root inside an extracted update.

    A packaged release .zip asset places files directly at the
    archive root alongside download.zip. If the asset instead wraps
    everything inside a single top-level folder, that folder is
    returned instead.
    """
    candidates = [
        entry
        for entry in extract_dir.iterdir()
        if entry.name != "download.zip"
    ]
    if len(candidates) == 1 and candidates[0].is_dir():
        return candidates[0]
    return extract_dir


def backup_application(
    app_dir: Path,
    current_version: str,
    backup_root: Path | None = None,
) -> Path:
    """
    Copy the current application's .py source files into a
    timestamped backup folder before an in-place source update is
    applied. Script/dev-mode safety net only.
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if backup_root is None:
        backup_root = app_dir / UPDATES_DIRNAME / BACKUPS_DIRNAME
    backup_dir = backup_root / f"v{version_slug(current_version)}_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for entry in app_dir.iterdir():
        if entry.name in PROTECTED_NAMES:
            continue
        destination = backup_dir / entry.name
        if entry.is_dir():
            shutil.copytree(
                entry,
                destination,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        else:
            shutil.copy2(entry, destination)
    return backup_dir


def apply_extracted_update(
    source_root: Path,
    app_dir: Path,
) -> list[Path]:
    """
    Copy every file from an extracted update over the running
    application directory, overwriting existing files in place.
    Script/dev-mode only — never used for a frozen exe build.
    """
    applied: list[Path] = []
    for source_path in sorted(source_root.rglob("*")):
        if not source_path.is_file():
            continue
        relative = source_path.relative_to(source_root)
        if relative.parts and relative.parts[0] in PROTECTED_NAMES:
            continue
        if "__pycache__" in relative.parts:
            continue
        if source_path.name == "download.zip":
            continue
        destination = app_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        applied.append(destination)
    return applied


def apply_staged_update(
    staged_dir: Path,
    app_dir: Path | None = None,
    current_version: str = APP_VERSION,
) -> InstallResult:
    """
    Apply an already-downloaded staged source update in place.
    Script/dev-mode only.
    """
    if app_dir is None:
        app_dir = application_dir()
    source_root = find_release_root(staged_dir)
    backup_dir = backup_application(app_dir, current_version)
    applied = apply_extracted_update(source_root, app_dir)
    return InstallResult(
        backup_dir=backup_dir,
        staged_dir=staged_dir,
        applied_files=tuple(applied),
    )


def install_update(
    info: UpdateInfo,
    app_dir: Path | None = None,
    dest_dir: Path | None = None,
    timeout_seconds: int = 60,
) -> InstallResult:
    """
    Download, back up, and apply a source-file update in one call.
    Script/dev-mode only. Raises if called with asset_kind == "exe"
    or asset_kind == "none"; use stage_exe_update() +
    apply_exe_update() for the exe path instead, and never call this
    at all when no compatible asset was found.
    """
    if info.asset_kind != "zip":
        raise ValueError(
            "install_update() applies source-file updates from a "
            "packaged .zip asset and cannot be used for asset_kind="
            f"'{info.asset_kind}'. Use stage_exe_update() and "
            "apply_exe_update() for an 'exe' asset, or skip entirely "
            "for 'none'."
        )
    staged_dir = download_update(
        info,
        dest_dir=dest_dir,
        timeout_seconds=timeout_seconds,
    )
    return apply_staged_update(
        staged_dir,
        app_dir=app_dir,
        current_version=APP_VERSION,
    )


# ============================================================
# Frozen exe self-update path (replaces the running .exe file)
# ============================================================

def backup_exe(
    target_exe_path: Path,
    current_version: str,
    backup_root: Path | None = None,
) -> Path:
    """
    Copy the current .exe file to a timestamped backup location
    before it is replaced. Safe to do while the exe is running, since
    this only reads/copies the file rather than deleting or moving it.
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if backup_root is None:
        backup_root = (
            target_exe_path.parent / UPDATES_DIRNAME / BACKUPS_DIRNAME
        )
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = (
        backup_root
        / f"{target_exe_path.stem}_v{version_slug(current_version)}_"
        f"{stamp}{target_exe_path.suffix}"
    )
    shutil.copy2(target_exe_path, backup_path)
    return backup_path


def stage_exe_update(
    info: UpdateInfo,
    dest_dir: Path | None = None,
    timeout_seconds: int = 180,
) -> Path:
    """
    Download a compiled .exe release asset and stage it under
    updates/v<version>/staged_update.exe. Does not touch the running
    executable in any way — this only downloads and verifies.

    Verifies the download against the asset's published sha256 digest
    when GitHub provided one (info.asset_digest), raising ValueError
    on a mismatch before the file is ever used.
    """
    if not info.download_url:
        raise ValueError("No download URL is available for this release.")
    if dest_dir is None:
        dest_dir = (
            application_dir()
            / UPDATES_DIRNAME
            / f"v{version_slug(info.latest_version)}"
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        info.download_url,
        headers={"User-Agent": APP_NAME.replace(" ", "")},
    )
    with urllib.request.urlopen(
        request,
        timeout=timeout_seconds,
    ) as response:
        data = response.read()
    if info.asset_digest:
        verify_digest(data, info.asset_digest)
    staged_path = dest_dir / STAGED_EXE_FILENAME
    staged_path.write_bytes(data)
    return staged_path


def build_apply_batch_script(
    new_exe_path: Path,
    target_exe_path: Path,
    relaunch: bool = True,
) -> Path:
    """
    Write a small Windows batch script that waits for this process to
    release its own executable file, replaces it with the staged
    update, and optionally relaunches it.

    A running Windows executable's file generally cannot be deleted
    or overwritten by another process while it is still executing.
    Rather than attempting the replace from within the still-running
    process, this script is launched as a separate detached process
    right before the application exits. It retries the delete/move
    for up to ~20 seconds, which comfortably covers the short delay
    between launching this script and the calling process actually
    exiting and releasing its file handle.
    """
    relaunch_flag = "1" if relaunch else "0"
    script_lines = [
        "@echo off",
        "setlocal EnableDelayedExpansion",
        f'set "NEWEXE={new_exe_path}"',
        f'set "TARGET={target_exe_path}"',
        f'set "RELAUNCH={relaunch_flag}"',
        "set /a attempts=0",
        ":retry",
        "set /a attempts+=1",
        'del /f /q "%TARGET%" 2>nul',
        'if exist "%TARGET%" (',
        "    if !attempts! LSS 20 (",
        "        timeout /t 1 /nobreak >nul",
        "        goto retry",
        "    ) else (",
        "        exit /b 1",
        "    )",
        ")",
        'move /y "%NEWEXE%" "%TARGET%" >nul',
        'if "%RELAUNCH%"=="1" (',
        '    start "" "%TARGET%"',
        ")",
        'del /f /q "%~f0"',
        "",
    ]
    script_path = new_exe_path.parent / "apply_update.bat"
    script_path.write_text(
        "\r\n".join(script_lines),
        encoding="utf-8",
    )
    return script_path


def launch_apply_script(script_path: Path) -> None:
    """
    Launch the apply batch script as a detached background process,
    so it keeps running after this Python process exits.

    Windows-only, since the exe self-update flow only applies to
    Windows PyInstaller builds.
    """
    if sys.platform != "win32":
        raise RuntimeError(
            "Exe self-update is only supported on Windows."
        )
    detached_process = 0x00000008
    create_new_process_group = 0x00000200
    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        creationflags=detached_process | create_new_process_group,
        close_fds=True,
    )


def apply_exe_update(
    staged_exe_path: Path,
    target_exe_path: Path | None = None,
    current_version: str = APP_VERSION,
    relaunch: bool = True,
) -> Path:
    """
    Begin the exe self-update swap.

    Backs up the current .exe, writes a batch script that waits for
    this process to release its own file, replaces it with the staged
    download, and optionally relaunches it, then launches that script
    as a detached process.

    The CALLER is responsible for exiting the application (e.g.
    window.destroy() then sys.exit()) immediately after calling this
    — the swap can only complete once this process' file handle on
    its own exe is released, which is why the batch script retries
    for several seconds rather than acting immediately.

    Returns the path to the launched batch script.
    """
    if target_exe_path is None:
        if not is_frozen():
            raise RuntimeError(
                "apply_exe_update() only applies when running as a "
                "frozen (PyInstaller) executable."
            )
        target_exe_path = Path(sys.executable).resolve()
    backup_exe(target_exe_path, current_version)
    script_path = build_apply_batch_script(
        staged_exe_path.resolve(),
        target_exe_path,
        relaunch=relaunch,
    )
    launch_apply_script(script_path)
    return script_path


def open_releases_page(
    url: str = RELEASES_URL,
) -> None:
    webbrowser.open(url)
