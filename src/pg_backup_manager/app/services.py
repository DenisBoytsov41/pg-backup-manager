from __future__ import annotations

import sys
from pathlib import Path

from pg_backup_manager.domain.models import AppSettings, BackupProfile
from pg_backup_manager.domain.validators import validate_profile, validate_scheduler_settings
from pg_backup_manager.infrastructure.config_store import JsonConfigStore
from pg_backup_manager.infrastructure.scheduler import ScheduledTaskInfo, WindowsTaskScheduler
from pg_backup_manager.shared.errors import ValidationError
from pg_backup_manager.shared.paths import get_app_dir, sanitize_file_name


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

    def validate_profile(self, profile: BackupProfile) -> None:
        validate_profile(profile)

    def get_profile_file_name(self, profile: BackupProfile) -> str:
        safe_name = sanitize_file_name(profile.profile_name, fallback="profile")
        return f"{safe_name}.json"


class AppSettingsService:
    def __init__(self, config_store: JsonConfigStore) -> None:
        self._config_store = config_store

    def load_settings(self, path: str) -> AppSettings:
        return self._config_store.load_app_settings(path)

    def save_settings(self, path: str, settings: AppSettings) -> None:
        self._config_store.save_app_settings(path, settings)

    def register_recent_profile(self, settings: AppSettings, profile_path: str) -> AppSettings:
        normalized = str(Path(profile_path).expanduser().resolve(strict=False))

        recent = [item for item in settings.recent_profile_paths if item != normalized]
        recent.insert(0, normalized)

        settings.last_profile_path = normalized
        settings.recent_profile_paths = recent[:10]
        return settings


class SchedulerService:
    def __init__(self, scheduler: WindowsTaskScheduler | None = None) -> None:
        self._scheduler = scheduler or WindowsTaskScheduler()

    def build_task_run_command(self, profile_path: str) -> str:
        normalized_profile_path = str(Path(profile_path).expanduser().resolve(strict=False))

        if getattr(sys, "frozen", False):
            executable = str(Path(sys.executable).resolve())
            return f'"{executable}" run-profile "{normalized_profile_path}"'

        python_executable = str(Path(sys.executable).resolve())
        project_root = str(Path(get_app_dir()).resolve())
        src_path = str((Path(project_root) / "src").resolve())

        return (
            'cmd.exe /c '
            f'"cd /d ""{project_root}"" && '
            f'set ""PYTHONPATH={src_path}"" && '
            f'""{python_executable}"" -m pg_backup_manager run-profile ""{normalized_profile_path}"""'
        )

    def create_or_update_task(
        self,
        *,
        profile: BackupProfile,
        profile_path: str,
        run_password: str | None = None,
    ) -> str:
        if not profile.scheduler.enabled:
            raise ValidationError("Планировщик отключён в настройках профиля.")

        validate_scheduler_settings(
            schedule_type=profile.scheduler.schedule_type,
            start_time=profile.scheduler.start_time,
            task_name=profile.scheduler.task_name,
            days_of_week=profile.scheduler.days_of_week,
        )

        task_run_command = self.build_task_run_command(profile_path)

        return self._scheduler.create_or_update_task(
            task_name=profile.scheduler.task_name,
            task_run_command=task_run_command,
            schedule_type=profile.scheduler.schedule_type,
            start_time=profile.scheduler.start_time,
            days_of_week=profile.scheduler.days_of_week,
            run_user=profile.scheduler.run_user,
            run_password=run_password,
            run_with_highest_privileges=profile.scheduler.run_with_highest_privileges,
        )

    def delete_task(self, profile: BackupProfile) -> str:
        task_name = profile.scheduler.task_name.strip()
        if not task_name:
            raise ValidationError("Не указано имя задачи Планировщика.")
        return self._scheduler.delete_task(task_name)

    def query_task(self, profile: BackupProfile) -> ScheduledTaskInfo:
        task_name = profile.scheduler.task_name.strip()
        if not task_name:
            raise ValidationError("Не указано имя задачи Планировщика.")
        return self._scheduler.query_task(task_name)

    def run_task(self, profile: BackupProfile) -> str:
        task_name = profile.scheduler.task_name.strip()
        if not task_name:
            raise ValidationError("Не указано имя задачи Планировщика.")
        return self._scheduler.run_task(task_name)