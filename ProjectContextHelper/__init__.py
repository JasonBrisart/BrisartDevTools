"""
Project Context Helper

A no-dependency utility that creates structured project
context bundles for documentation, archival snapshots,
AI-assisted development, code review, and project handoff.
"""

from constants import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    REPOSITORY_URL,
)

from core import create_context

from models import (
    BuildResult,
    FileRecord,
    ScanSettings,
    SkipRecord,
)

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "AUTHOR",
    "REPOSITORY_URL",
    "BuildResult",
    "FileRecord",
    "ScanSettings",
    "SkipRecord",
    "create_context",
]