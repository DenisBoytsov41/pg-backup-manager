from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    file_name = globals().get("__file__")
    if file_name:
        return Path(file_name).resolve().parent.parent.parent

    return Path.cwd()


def expand_env_path(value: str) -> str:
    if not value:
        return value
    return os.path.expandvars(value)


def normalize_path(value: str) -> Path:
    return Path(expand_env_path(value)).expanduser().resolve()


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


def build_run_log_name(profile_name: str, timestamp: str) -> str:
    safe_name = profile_name.strip().replace(" ", "_") or "profile"
    return f"{safe_name}_{timestamp}.log"


def build_dump_file_name(database_name: str, timestamp: str) -> str:
    safe_name = database_name.strip().replace(" ", "_") or "database"
    return f"{safe_name}_{timestamp}.backup"


def build_globals_file_name(timestamp: str) -> str:
    return f"globals_{timestamp}.sql"