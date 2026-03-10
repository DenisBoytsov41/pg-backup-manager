from __future__ import annotations

import json
from pathlib import Path

from pg_backup_manager.domain.models import AppSettings, BackupProfile
from pg_backup_manager.shared.errors import ConfigError


class JsonConfigStore:
    def load_profile(self, path: str) -> BackupProfile:
        file_path = Path(path)

        if not file_path.exists():
            raise ConfigError(f"Файл профиля не найден: {file_path}")

        try:
            with file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Ошибка JSON в профиле {file_path}: {exc}") from exc
        except OSError as exc:
            raise ConfigError(f"Ошибка чтения профиля {file_path}: {exc}") from exc

        return BackupProfile.from_dict(data)

    def save_profile(self, path: str, profile: BackupProfile) -> None:
        file_path = Path(path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8") as file:
                json.dump(profile.to_dict(), file, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise ConfigError(f"Ошибка записи профиля {file_path}: {exc}") from exc

    def load_app_settings(self, path: str) -> AppSettings:
        file_path = Path(path)

        if not file_path.exists():
            return AppSettings()

        try:
            with file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Ошибка JSON в настройках приложения {file_path}: {exc}") from exc
        except OSError as exc:
            raise ConfigError(f"Ошибка чтения настроек приложения {file_path}: {exc}") from exc

        return AppSettings.from_dict(data)

    def save_app_settings(self, path: str, settings: AppSettings) -> None:
        file_path = Path(path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8") as file:
                json.dump(settings.to_dict(), file, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise ConfigError(f"Ошибка записи настроек приложения {file_path}: {exc}") from exc