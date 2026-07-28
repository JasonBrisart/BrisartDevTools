from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import io
import json
import urllib.error
import urllib.request
import webbrowser
import zipfile

from constants import (
    APP_NAME,
    APP_VERSION,
    RELEASES_URL,
    UPDATE_CHECK_URL,
)

# Downloaded updates are staged here, relative to the application directory.
# This folder name is already part of DEFAULT_EXCLUDE_DIRS, so staged updates
# never get swept into an export.
UPDATES_DIRNAME = "updates"


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


def check_for_updates(
    timeout_seconds: int = 6,
) -> UpdateInfo:
    """
    Check GitHub Releases for the newest release.
    """
    try:
        request = urllib.request.Request(
            UPDATE_CHECK_URL,
            headers={
                "User-Agent": APP_NAME.replace(" ", "")
            },
        )
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
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
    Download and stage an available update.

    The release archive is downloaded and, when it is a valid ZIP,
    extracted into a versioned folder under the application's
    'updates/' directory. The staged files are NOT applied over the
    running application automatically; the destination path is
    returned so the update can be reviewed and swapped in manually.

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


def open_releases_page(
    url: str = RELEASES_URL,
) -> None:
    """
    Open GitHub Releases page.
    """
    webbrowser.open(url)