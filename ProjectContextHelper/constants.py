from models import ScanSettings

APP_NAME = "Project Context Helper"
APP_VERSION = "2.0.0"
AUTHOR = "Jason Brisart"

REPOSITORY_NAME = "BrisartDevTools"
REPOSITORY_URL = "https://github.com/JasonBrisart/BrisartDevTools"
RELEASES_URL = "https://github.com/JasonBrisart/BrisartDevTools/releases"
UPDATE_CHECK_URL = "https://api.github.com/repos/JasonBrisart/BrisartDevTools/releases/latest"

EXPORTS_DIRNAME = "PROJECT_CONTEXT_EXPORTS"

CONTEXT_FILENAME = "PROJECT_CONTEXT.md"
MANIFEST_FILENAME = "PROJECT_MANIFEST.json"
SUMMARY_FILENAME = "PROJECT_SUMMARY.txt"
SNAPSHOT_FILENAME = "PROJECT_SNAPSHOT.zip"
SETTINGS_FILENAME = "PROJECT_CONTEXT_SETTINGS.json"

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

EXPANDED_EXTENSIONS = DEFAULT_EXTENSIONS | {
    ".rst",
    ".log",
    ".env.example",
    ".sample",
    ".template",
    ".lock",
}

ARCHIVE_EXTENSIONS = EXPANDED_EXTENSIONS | {
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

PROFILE_STANDARD = "standard"
PROFILE_EXPANDED = "expanded"
PROFILE_ARCHIVE = "archive"

VALID_PROFILES = {
    PROFILE_STANDARD,
    PROFILE_EXPANDED,
    PROFILE_ARCHIVE,
}

DEFAULT_MAX_FILE_BYTES = 350_000
DEFAULT_MAX_TOTAL_BYTES = 5_000_000

EXPANDED_MAX_FILE_BYTES = 500_000
EXPANDED_MAX_TOTAL_BYTES = 10_000_000

ARCHIVE_MAX_FILE_BYTES = 1_000_000
ARCHIVE_MAX_TOTAL_BYTES = 25_000_000


def settings_for_profile(profile: str) -> ScanSettings:
    """
    Build ScanSettings from a profile name.

    Profiles:
    - standard: clean everyday project context export.
    - expanded: includes more supporting files and a larger size budget.
    - archive: broadest source-code-oriented archival profile.
    """
    profile = profile.lower().strip()

    if profile not in VALID_PROFILES:
        raise ValueError(f"Invalid profile: {profile}")

    settings = ScanSettings(profile=profile)

    settings.exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    settings.exclude_files = set(DEFAULT_EXCLUDE_FILES)
    settings.exclude_suffixes = set(DEFAULT_EXCLUDE_SUFFIXES)

    if profile == PROFILE_STANDARD:
        settings.include_extensions = set(DEFAULT_EXTENSIONS)
        settings.max_file_bytes = DEFAULT_MAX_FILE_BYTES
        settings.max_total_bytes = DEFAULT_MAX_TOTAL_BYTES

    elif profile == PROFILE_EXPANDED:
        settings.include_extensions = set(EXPANDED_EXTENSIONS)
        settings.max_file_bytes = EXPANDED_MAX_FILE_BYTES
        settings.max_total_bytes = EXPANDED_MAX_TOTAL_BYTES

    elif profile == PROFILE_ARCHIVE:
        settings.include_extensions = set(ARCHIVE_EXTENSIONS)
        settings.max_file_bytes = ARCHIVE_MAX_FILE_BYTES
        settings.max_total_bytes = ARCHIVE_MAX_TOTAL_BYTES

    return settings