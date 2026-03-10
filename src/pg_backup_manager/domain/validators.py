from __future__ import annotations

import os
import re

from pg_backup_manager.domain.models import BackupProfile, ScheduleType
from pg_backup_manager.shared.errors import ValidationError


_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def validate_profile(profile: BackupProfile) -> None:
    errors: list[str] = []

    if not profile.profile_name.strip():
        errors.append("Не указано имя профиля.")

    if not profile.postgres.host.strip():
        errors.append("Не указан host PostgreSQL.")

    if not isinstance(profile.postgres.port, int) or not (1 <= profile.postgres.port <= 65535):
        errors.append("Порт PostgreSQL должен быть числом от 1 до 65535.")

    if not profile.postgres.databases:
        errors.append("Не указана ни одна база данных для резервного копирования.")

    if not profile.postgres.user.strip():
        errors.append("Не указан пользователь PostgreSQL.")

    if not profile.postgres.pg_dump_path.strip():
        errors.append("Не указан путь к pg_dump.exe.")

    if not profile.backup.backup_dir.strip():
        errors.append("Не указана папка для хранения backup.")

    if profile.backup.retention_days < 0:
        errors.append("Период хранения backup не может быть отрицательным.")

    if profile.scheduler.enabled:
        validate_scheduler_settings(
            schedule_type=profile.scheduler.schedule_type,
            start_time=profile.scheduler.start_time,
            task_name=profile.scheduler.task_name,
            days_of_week=profile.scheduler.days_of_week,
            errors=errors,
        )

    if errors:
        raise ValidationError("\n".join(errors))


def validate_scheduler_settings(
    schedule_type: ScheduleType,
    start_time: str,
    task_name: str,
    days_of_week: list[str],
    errors: list[str] | None = None,
) -> None:
    local_errors = errors if errors is not None else []

    if not task_name.strip():
        local_errors.append("Не указано имя задачи Планировщика.")

    if not _TIME_PATTERN.match(start_time):
        local_errors.append("Время запуска должно быть в формате HH:MM.")

    else:
        hours, minutes = start_time.split(":")
        if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
            local_errors.append("Время запуска содержит недопустимые часы или минуты.")

    if schedule_type == ScheduleType.WEEKLY and not days_of_week:
        local_errors.append("Для еженедельного расписания нужно указать хотя бы один день недели.")

    if errors is None and local_errors:
        raise ValidationError("\n".join(local_errors))


def validate_existing_executable(path: str, field_name: str) -> None:
    if not path.strip():
        raise ValidationError(f"Не указан путь к {field_name}.")

    if not os.path.isfile(path):
        raise ValidationError(f"Файл {field_name} не найден: {path}")