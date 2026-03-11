from __future__ import annotations

from pg_backup_manager.domain.models import (
    BackupProfile,
    BackupSettings,
    LoggingSettings,
    PostgresSettings,
    ScheduleType,
    SchedulerSettings,
)
from pg_backup_manager.shared.errors import ValidationError
from pg_backup_manager.ui.form_state import MainWindowState


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_profile_from_state(state: MainWindowState) -> BackupProfile:
    try:
        port = int(state.port_var.get().strip() or "5432")
    except ValueError as exc:
        raise ValidationError("Порт PostgreSQL должен быть числом.") from exc

    try:
        retention_days = int(state.retention_days_var.get().strip() or "30")
    except ValueError as exc:
        raise ValidationError("Количество дней хранения должно быть числом.") from exc

    schedule_value = state.schedule_type_var.get().strip() or ScheduleType.DISABLED.value
    try:
        schedule_type = ScheduleType(schedule_value)
    except ValueError:
        schedule_type = ScheduleType.DISABLED

    return BackupProfile(
        schema_version=1,
        profile_name=state.profile_name_var.get().strip() or "New Profile",
        postgres=PostgresSettings(
            host=state.host_var.get().strip(),
            port=port,
            databases=split_csv(state.databases_var.get()),
            user=state.user_var.get().strip(),
            password=state.password_var.get(),
            pg_dump_path=state.pg_dump_path_var.get().strip(),
            pg_dumpall_path=state.pg_dumpall_path_var.get().strip(),
        ),
        backup=BackupSettings(
            backup_dir=state.backup_dir_var.get().strip(),
            retention_days=retention_days,
            dump_globals=bool(state.dump_globals_var.get()),
            naming_pattern=state.naming_pattern_var.get().strip() or "{database}_{timestamp}",
        ),
        logging=LoggingSettings(
            main_log_name=state.main_log_name_var.get().strip() or "backup.log",
            log_level=state.log_level_var.get().strip() or "INFO",
        ),
        scheduler=SchedulerSettings(
            enabled=bool(state.scheduler_enabled_var.get()),
            task_name=state.task_name_var.get().strip(),
            schedule_type=schedule_type,
            start_time=state.start_time_var.get().strip() or "02:00",
            days_of_week=split_csv(state.days_of_week_var.get()),
            run_user=state.run_user_var.get().strip(),
            run_with_highest_privileges=bool(state.run_with_highest_privileges_var.get()),
        ),
    )


def populate_state_from_profile(state: MainWindowState, profile: BackupProfile) -> None:
    state.profile_name_var.set(profile.profile_name)

    state.host_var.set(profile.postgres.host)
    state.port_var.set(str(profile.postgres.port))
    state.databases_var.set(", ".join(profile.postgres.databases))
    state.user_var.set(profile.postgres.user)
    state.password_var.set(profile.postgres.password)
    state.pg_dump_path_var.set(profile.postgres.pg_dump_path)
    state.pg_dumpall_path_var.set(profile.postgres.pg_dumpall_path)

    state.backup_dir_var.set(profile.backup.backup_dir)
    state.retention_days_var.set(str(profile.backup.retention_days))
    state.dump_globals_var.set(profile.backup.dump_globals)
    state.naming_pattern_var.set(profile.backup.naming_pattern)

    state.main_log_name_var.set(profile.logging.main_log_name)
    state.log_level_var.set(profile.logging.log_level)

    state.scheduler_enabled_var.set(profile.scheduler.enabled)
    state.task_name_var.set(profile.scheduler.task_name)
    state.schedule_type_var.set(profile.scheduler.schedule_type.value)
    state.start_time_var.set(profile.scheduler.start_time)
    state.days_of_week_var.set(", ".join(profile.scheduler.days_of_week))
    state.run_user_var.set(profile.scheduler.run_user)
    state.run_with_highest_privileges_var.set(profile.scheduler.run_with_highest_privileges)

    state.reset_runtime_fields()
    state.reset_scheduler_status()
    state.mark_clean()