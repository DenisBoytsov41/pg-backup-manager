from __future__ import annotations

import os
import re
import string

from pg_backup_manager.domain.models import BackupProfile, ScheduleType
from pg_backup_manager.shared.errors import ValidationError


_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")
_ALLOWED_NAMING_FIELDS = {"database", "timestamp", "profile"}


def validate_profile(profile: BackupProfile, *, strict_runtime: bool = False) -> None:
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

    validate_naming_pattern(profile.backup.naming_pattern, errors=errors)

    if profile.backup.dump_globals and not profile.postgres.pg_dumpall_path.strip():
        errors.append("Включена выгрузка globals, но не указан путь к pg_dumpall.exe.")

    if profile.scheduler.enabled:
        if profile.scheduler.schedule_type == ScheduleType.DISABLED:
            errors.append(
                "Для включённого Планировщика нужно выбрать тип расписания, отличный от DISABLED."
            )

        validate_scheduler_settings(
            schedule_type=profile.scheduler.schedule_type,
            start_time=profile.scheduler.start_time,
            task_name=profile.scheduler.task_name,
            days_of_week=profile.scheduler.days_of_week,
            errors=errors,
        )

    if errors:
        raise ValidationError("\n".join(errors))

    if strict_runtime:
        validate_existing_executable(profile.postgres.pg_dump_path, "pg_dump.exe")

        if profile.backup.dump_globals:
            validate_existing_executable(profile.postgres.pg_dumpall_path, "pg_dumpall.exe")


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

    if schedule_type == ScheduleType.DISABLED:
        local_errors.append("Тип расписания Планировщика не должен быть DISABLED.")

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


def validate_naming_pattern(
    naming_pattern: str,
    errors: list[str] | None = None,
) -> None:
    local_errors = errors if errors is not None else []
    pattern = naming_pattern.strip()

    if not pattern:
        local_errors.append("Не указан шаблон имени backup-файла.")
        if errors is None and local_errors:
            raise ValidationError("\n".join(local_errors))
        return

    formatter = string.Formatter()
    unknown_fields: list[str] = []

    try:
        for _, field_name, _, _ in formatter.parse(pattern):
            if field_name is None:
                continue
            if field_name not in _ALLOWED_NAMING_FIELDS and field_name not in unknown_fields:
                unknown_fields.append(field_name)
    except ValueError as exc:
        local_errors.append(f"Некорректный шаблон имени backup-файла: {exc}")
    else:
        if "{database}" not in pattern:
            local_errors.append(
                "Шаблон имени backup-файла должен содержать плейсхолдер {database}."
            )

        if "{timestamp}" not in pattern:
            local_errors.append(
                "Шаблон имени backup-файла должен содержать плейсхолдер {timestamp}."
            )

        if unknown_fields:
            local_errors.append(
                "В шаблоне имени backup-файла используются недопустимые плейсхолдеры: "
                + ", ".join(sorted(unknown_fields))
                + ". Допустимы только: {database}, {timestamp}, {profile}."
            )

        if not unknown_fields:
            try:
                pattern.format(
                    database="database",
                    timestamp="2026-03-10_02-00-00",
                    profile="profile",
                )
            except (ValueError, IndexError) as exc:
                local_errors.append(f"Некорректный шаблон имени backup-файла: {exc}")

    if errors is None and local_errors:
        raise ValidationError("\n".join(local_errors))


def validate_existing_executable(path: str, field_name: str) -> None:
    if not path.strip():
        raise ValidationError(f"Не указан путь к {field_name}.")

    if not os.path.isfile(path):
        raise ValidationError(f"Файл {field_name} не найден: {path}")