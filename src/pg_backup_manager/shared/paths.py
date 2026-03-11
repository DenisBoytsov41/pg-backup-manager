from __future__ import annotations

import os
import re
import sys
from pathlib import Path


_INVALID_FILE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    file_name = globals().get("__file__")
    if file_name:
        current = Path(file_name).resolve()

        if len(current.parents) >= 4 and current.parents[2].name == "src":
            return current.parents[3]

        return current.parent

    return Path.cwd()


def expand_env_path(value: str) -> str:
    if not value:
        return value
    return os.path.expandvars(value)


def normalize_path(value: str | Path) -> Path:
    if isinstance(value, Path):
        return value.expanduser().resolve(strict=False)

    expanded = expand_env_path(value).strip()
    if not expanded:
        return Path.cwd()

    return Path(expanded).expanduser().resolve(strict=False)


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_default_app_data_dir(app_name: str = "pg-backup-manager") -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / app_name
    return Path.home() / f".{app_name}"


def get_default_app_settings_path(app_name: str = "pg-backup-manager") -> Path:
    return get_default_app_data_dir(app_name) / "app-settings.json"


def sanitize_file_name(value: str, fallback: str = "file") -> str:
    safe_fallback = fallback.strip() or "file"
    safe_fallback = _INVALID_FILE_NAME_CHARS.sub("_", safe_fallback)
    safe_fallback = re.sub(r"\s+", "_", safe_fallback).strip(" ._") or "file"

    normalized = value.strip()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = _INVALID_FILE_NAME_CHARS.sub("_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.rstrip(" .")
    normalized = normalized.strip("._")

    if not normalized:
        normalized = safe_fallback

    if normalized.upper() in _WINDOWS_RESERVED_NAMES:
        normalized = f"{safe_fallback}_{normalized}"

    return normalized[:240]


def build_run_log_name(profile_name: str, timestamp: str) -> str:
    safe_name = sanitize_file_name(profile_name, fallback="profile")
    return f"{safe_name}_{timestamp}.log"


def build_dump_file_name(
    database_name: str,
    timestamp: str,
    naming_pattern: str = "{database}_{timestamp}",
    profile_name: str = "",
) -> str:
    rendered = naming_pattern.format(
        database=database_name.strip() or "database",
        timestamp=timestamp,
        profile=profile_name.strip() or "profile",
    )
    safe_name = sanitize_file_name(rendered, fallback="database")
    return f"{safe_name}.backup"


def build_globals_file_name(timestamp: str, profile_name: str = "") -> str:
    base_name = f"globals_{profile_name}_{timestamp}" if profile_name.strip() else f"globals_{timestamp}"
    safe_name = sanitize_file_name(base_name, fallback="globals")
    return f"{safe_name}.sql"