from __future__ import annotations

from pathlib import Path

from pg_backup_manager.domain.models import AppSettings, BackupProfile
from pg_backup_manager.domain.validators import validate_profile
from pg_backup_manager.infrastructure.config_store import JsonConfigStore


class ProfileService:
    def __init__(self, config_store: JsonConfigStore) -> None:
        self._config_store = config_store

    def create_default_profile(self, profile_name: str = "New Profile") -> BackupProfile:
        profile = BackupProfile()
        profile.profile_name = profile_name
        return profile

    def load_profile(self, path: str) -> BackupProfile:
        return self._config_store.load_profile(path)

    def save_profile(self, path: str, profile: BackupProfile) -> None:
        validate_profile(profile)
        self._config_store.save_profile(path, profile)

    def get_profile_file_name(self, profile: BackupProfile) -> str:
        safe_name = profile.profile_name.strip() or "profile"
        safe_name = safe_name.replace(" ", "_")
        return f"{safe_name}.json"


class AppSettingsService:
    def __init__(self, config_store: JsonConfigStore) -> None:
        self._config_store = config_store

    def load_settings(self, path: str) -> AppSettings:
        return self._config_store.load_app_settings(path)

    def save_settings(self, path: str, settings: AppSettings) -> None:
        self._config_store.save_app_settings(path, settings)

    def register_recent_profile(self, settings: AppSettings, profile_path: str) -> AppSettings:
        normalized = str(Path(profile_path))

        recent = [item for item in settings.recent_profile_paths if item != normalized]
        recent.insert(0, normalized)

        settings.last_profile_path = normalized
        settings.recent_profile_paths = recent[:10]
        return settings