from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import datetime
import io
import json
import shutil
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
)
# Downloaded updates are staged here, relative to the application directory.
# This folder name is already part of DEFAULT_EXCLUDE_DIRS, so staged updates
# never get swept into an export.
UPDATES_DIRNAME = "updates"
# Backups of the application's own files are written here before an update
# is ever applied in place. Also under 'updates/', so it is excluded from
# exports the same way staged downloads are.
BACKUPS_DIRNAME = "backups"
# Names that are never copied INTO the application directory during an
# in-place update, and never copied FROM the application directory during
# a pre-update backup. This keeps the updater from ever touching its own
# staging area, backups, caches, or version control metadata.
PROTECTED_NAMES = {
    UPDATES_DIRNAME,
    EXPORTS_DIRNAME,
    "__pycache__",
    ".git",
    "download.zip",
}
@dataclass(slots=True)
class UpdateInfo:
    """
    Result of an update check.
    """
    update_available: bool
    current_version: str
    latest_version: str
    message: str
    release_url: str
    download_url: str = ""
@dataclass(slots=True)
class InstallResult:
    """
    Result of applying a staged update in place.
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
    release-1.4
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
    """
    Return True if latest is newer than current.
    """
    return normalize_version(latest) > normalize_version(current)
def version_slug(value: str) -> str:
    """
    Build a filesystem-safe folder name from a version string.
    """
    slug = "".join(
        char
        for char in value
        if char.isalnum() or char in {".", "-", "_"}
    )
    return slug or "latest"
def resolve_download_url(payload: dict) -> str:
    """
    Pick the best download URL from a GitHub release payload.
    Prefers a packaged .zip release asset, then falls back to the
    auto-generated source zipball.
    """
    assets = payload.get("assets") or []
    for asset in assets:
        name = (asset.get("name") or "").lower()
        if name.endswith(".zip"):
            url = asset.get("browser_download_url")
            if url:
                return url
    return payload.get("zipball_url") or ""
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
    """
    try:
        request = urllib.request.Request(
            RELEASES_LIST_URL,
            headers={
                "User-Agent": APP_NAME.replace(" ", "")
            },
        )
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            releases = json.loads(
                response.read().decode("utf-8")
            )
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
        release_url = (
            payload.get("html_url")
            or RELEASES_URL
        )
        download_url = resolve_download_url(payload)
        if is_newer_version(
            latest_version,
            APP_VERSION,
        ):
            return UpdateInfo(
                update_available=True,
                current_version=APP_VERSION,
                latest_version=latest_version,
                message=(
                    f"Update available: "
                    f"{latest_version} "
                    f"(current: {APP_VERSION})"
                ),
                release_url=release_url,
                download_url=download_url,
            )
        return UpdateInfo(
            update_available=False,
            current_version=APP_VERSION,
            latest_version=latest_version,
            message=(
                f"You are running the latest version "
                f"({APP_VERSION})."
            ),
            release_url=release_url,
            download_url=download_url,
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
def application_dir() -> Path:
    """
    Return the directory the application package lives in.
    """
    return Path(__file__).resolve().parent
def download_update(
    info: UpdateInfo,
    dest_dir: Path | None = None,
    timeout_seconds: int = 60,
) -> Path:
    """
    Download and extract an available update into a staging folder.
    The release archive is downloaded and, when it is a valid ZIP,
    extracted into a versioned folder under the application's
    'updates/' directory. This step only stages the files; it does
    not touch the running application. Use apply_staged_update() (or
    install_update()) to actually copy the staged files over the
    application in place.
    Returns the staging directory the update was written to.
    """
    if not info.download_url:
        raise ValueError(
            "No download URL is available for this release."
        )
    if dest_dir is None:
        dest_dir = (
            application_dir()
            / UPDATES_DIRNAME
            / f"v{version_slug(info.latest_version)}"
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        info.download_url,
        headers={
            "User-Agent": APP_NAME.replace(" ", "")
        },
    )
    with urllib.request.urlopen(
        request,
        timeout=timeout_seconds,
    ) as response:
        data = response.read()
    archive_path = dest_dir / "download.zip"
    archive_path.write_bytes(data)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            archive.extractall(dest_dir)
    except zipfile.BadZipFile:
        # Not a zip payload; leave the raw download in place.
        pass
    return dest_dir
def find_release_root(extract_dir: Path) -> Path:
    """
    Locate the actual package root inside an extracted update.
    GitHub's auto-generated zipball wraps every file inside a single
    top-level folder such as 'JasonBrisart-BrisartDevTools-<sha>/'.
    A packaged release .zip asset, by contrast, usually places files
    directly at the archive root alongside download.zip.
    This returns whichever directory actually contains the update's
    files, so callers do not need to know which packaging style a
    given release used.
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
    Copy the current application files into a timestamped backup
    folder before an update is applied in place.
    This is the safety net for in-place updates: if an update is
    bad, unwanted, or applied incorrectly, the previous version's
    files remain available to be copied back manually.
    Returns the backup directory path.
    """
    stamp = (
        datetime.datetime.now()
        .strftime("%Y%m%d_%H%M%S")
    )
    if backup_root is None:
        backup_root = app_dir / UPDATES_DIRNAME / BACKUPS_DIRNAME
    backup_dir = (
        backup_root
        / f"v{version_slug(current_version)}_{stamp}"
    )
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
    This is an overwrite-copy, not a mirror/sync: files present in
    app_dir but absent from the update are left untouched and are
    not deleted. The 'updates' staging directory, export output
    directory, __pycache__, and .git are never used as a source or
    written to as a destination.
    Returns the list of destination files that were written.
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
    Apply an already-downloaded staged update in place.
    Always backs up the current application files first. This is
    the function to call once a user (or an auto-install setting)
    has decided a previously staged update should actually replace
    the running application's files.
    """
    if app_dir is None:
        app_dir = application_dir()
    source_root = find_release_root(staged_dir)
    backup_dir = backup_application(
        app_dir,
        current_version,
    )
    applied = apply_extracted_update(
        source_root,
        app_dir,
    )
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
    Download, back up, and apply an update in place in one call.
    Convenience wrapper combining download_update() and
    apply_staged_update() for callers (such as the CLI) that want a
    single-step auto-install rather than a separate stage/apply
    decision point.
    """
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
def open_releases_page(
    url: str = RELEASES_URL,
) -> None:
    """
    Open GitHub Releases page.
    """
    webbrowser.open(url)
