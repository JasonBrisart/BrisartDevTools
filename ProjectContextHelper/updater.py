from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.error
import urllib.request
import webbrowser

from constants import (
    APP_VERSION,
    RELEASES_URL,
    UPDATE_CHECK_URL,
)


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


def normalize_version(value: str) -> tuple[int, ...]:
    """
    Convert version strings such as:
    2.0.0
    v2.1.3
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
                "User-Agent": "ProjectContextHelper"
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


def open_releases_page(
    url: str = RELEASES_URL,
) -> None:
    """
    Open GitHub Releases page.
    """
    webbrowser.open(url)