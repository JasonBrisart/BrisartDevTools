from models import ScanSettings

APP_NAME = "Project Context Helper"
APP_VERSION = "2.1.5"
AUTHOR = "Jason Brisart"

# Release history now lives in changelog.py (single source of truth for
# release notes). The About tab imports it from there.

REPOSITORY_NAME = "BrisartDevTools"
REPOSITORY_URL = "https://github.com/JasonBrisart/BrisartDevTools"
RELEASES_URL = "https://github.com/JasonBrisart/BrisartDevTools/releases"
UPDATE_CHECK_URL = (
    "https://api.github.com/repos/"
    "JasonBrisart/BrisartDevTools/releases/latest"
)

EXPORTS_DIRNAME = "PROJECT_CONTEXT_EXPORTS"

CONTEXT_FILENAME = "PROJECT_CONTEXT.md"
MANIFEST_FILENAME = "PROJECT_MANIFEST.json"
SUMMARY_FILENAME = "PROJECT_SUMMARY.txt"
SNAPSHOT_FILENAME = "PROJECT_SNAPSHOT.zip"
SETTINGS_FILENAME = "PROJECT_CONTEXT_SETTINGS.json"

# ============================================================
# Profiles
#
# Two profiles are supported:
#   standard - fast, lightweight everyday export
#   archive  - maximum preservation (default)
#
# The former "expanded" profile was removed in v2.1.4. Its
# extra extensions were folded into the archive profile so
# archive remains the true capture-everything mode.
# ============================================================
PROFILE_STANDARD = "standard"
PROFILE_ARCHIVE = "archive"

DEFAULT_PROFILE = PROFILE_ARCHIVE

VALID_PROFILES = {
    PROFILE_STANDARD,
    PROFILE_ARCHIVE,
}

DEFAULT_EXTENSIONS = {
    ".py",
    ".json",
    ".csv",
    ".txt",
    ".md",
    ".toml",
    ".ini",
    ".cfg",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sql",
    ".xml",
    ".bat",
    ".ps1",
    ".sh",
    ".gitignore",
    ".dockerignore",
}

# Archive folds in the extra documentation/config extensions that
# used to live in the expanded profile, plus the broad source-code
# extension set for maximum preservation.
ARCHIVE_EXTENSIONS = DEFAULT_EXTENSIONS | {
    ".rst",
    ".log",
    ".env.example",
    ".sample",
    ".template",
    ".lock",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".r",
    ".m",
    ".mm",
    ".pl",
    ".lua",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "build",
    "dist",
    ".idea",
    ".vscode",
    "updates",
    EXPORTS_DIRNAME,
}

DEFAULT_EXCLUDE_FILES = {
    CONTEXT_FILENAME,
    MANIFEST_FILENAME,
    SUMMARY_FILENAME,
    SNAPSHOT_FILENAME,
    SETTINGS_FILENAME,
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
}

DEFAULT_EXCLUDE_SUFFIXES = {
    ".pem",
    ".key",
    ".crt",
    ".pfx",
    ".p12",
    ".sqlite",
    ".db",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".7z",
    ".rar",
}

DEFAULT_MAX_FILE_BYTES = 350_000
DEFAULT_MAX_TOTAL_BYTES = 5_000_000

ARCHIVE_MAX_FILE_BYTES = 2_000_000
ARCHIVE_MAX_TOTAL_BYTES = 100_000_000

STANDARD_SKIPPED_DETAILS_LIMIT = 100
ARCHIVE_SKIPPED_DETAILS_LIMIT = 1000


def apply_common_defaults(settings: ScanSettings) -> ScanSettings:
    """
    Apply shared default exclusion rules.
    """
    settings.exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    settings.exclude_files = set(DEFAULT_EXCLUDE_FILES)
    settings.exclude_suffixes = set(DEFAULT_EXCLUDE_SUFFIXES)
    return settings


def apply_standard_preset(settings: ScanSettings) -> ScanSettings:
    """
    Standard profile.
    Fast everyday export.
    Best for quick documentation, project overview,
    and lightweight AI context.
    """
    settings.include_extensions = set(DEFAULT_EXTENSIONS)
    settings.max_file_bytes = DEFAULT_MAX_FILE_BYTES
    settings.max_total_bytes = DEFAULT_MAX_TOTAL_BYTES
    settings.include_snapshot_zip = True
    settings.redact_sensitive_lines = True
    settings.include_hashes = False
    settings.include_line_counts = False
    settings.include_folder_tree = True
    settings.include_file_index = True
    settings.include_file_contents = False
    settings.include_skipped_details = False
    settings.timestamped_export_folder = True
    settings.skipped_details_limit = STANDARD_SKIPPED_DETAILS_LIMIT
    settings.require_complete_source = False
    return settings


def apply_archive_preset(settings: ScanSettings) -> ScanSettings:
    """
    Archive profile. Default profile.
    Maximum preservation mode.

    This mode requires complete source capture.
    If an eligible source file cannot be included,
    the build fails instead of producing a partial archive.
    """
    settings.include_extensions = set(ARCHIVE_EXTENSIONS)
    settings.max_file_bytes = ARCHIVE_MAX_FILE_BYTES
    settings.max_total_bytes = ARCHIVE_MAX_TOTAL_BYTES
    settings.include_snapshot_zip = True
    settings.redact_sensitive_lines = True
    settings.include_hashes = True
    settings.include_line_counts = True
    settings.include_folder_tree = True
    settings.include_file_index = True
    settings.include_file_contents = True
    settings.include_skipped_details = True
    settings.timestamped_export_folder = True
    settings.skipped_details_limit = ARCHIVE_SKIPPED_DETAILS_LIMIT
    settings.require_complete_source = True
    return settings


def settings_for_profile(profile: str) -> ScanSettings:
    """
    Build ScanSettings from a profile name.

    Profiles:
    - standard
    - archive (default)
    """
    profile = profile.lower().strip()

    if profile not in VALID_PROFILES:
        raise ValueError(f"Invalid profile: {profile}")

    settings = ScanSettings(profile=profile)
    settings = apply_common_defaults(settings)

    if profile == PROFILE_STANDARD:
        return apply_standard_preset(settings)

    if profile == PROFILE_ARCHIVE:
        return apply_archive_preset(settings)

    raise ValueError(f"Invalid profile: {profile}")
