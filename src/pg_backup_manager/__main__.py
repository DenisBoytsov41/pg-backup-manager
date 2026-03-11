from __future__ import annotations

import argparse

from pg_backup_manager.app.services import ProfileService, SchedulerService
from pg_backup_manager.domain.models import BackupProfile
from pg_backup_manager.infrastructure.backup_runner import BackupRunner
from pg_backup_manager.infrastructure.config_store import JsonConfigStore
from pg_backup_manager.infrastructure.scheduler import ScheduledTaskInfo
from pg_backup_manager.shared.errors import (
    BackupExecutionError,
    ConfigError,
    PgBackupManagerError,
    SchedulerError,
    ValidationError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pg_backup_manager",
        description="PG Backup Manager CLI",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "gui",
        help="Запустить графический интерфейс",
    )

    run_profile_parser = subparsers.add_parser(
        "run-profile",
        help="Выполнить backup по JSON-профилю",
    )
    run_profile_parser.add_argument(
        "profile_path",
        help="Путь к JSON-файлу профиля",
    )

    validate_profile_parser = subparsers.add_parser(
        "validate-profile",
        help="Проверить корректность JSON-профиля",
    )
    validate_profile_parser.add_argument(
        "profile_path",
        help="Путь к JSON-файлу профиля",
    )

    scheduler_create_parser = subparsers.add_parser(
        "scheduler-create",
        help="Создать или обновить задачу Планировщика по профилю",
    )
    scheduler_create_parser.add_argument(
        "profile_path",
        help="Путь к JSON-файлу профиля",
    )
    scheduler_create_parser.add_argument(
        "--run-password",
        dest="run_password",
        default=None,
        help="Пароль пользователя запуска задачи (если требуется)",
    )

    scheduler_query_parser = subparsers.add_parser(
        "scheduler-query",
        help="Проверить задачу Планировщика по профилю",
    )
    scheduler_query_parser.add_argument(
        "profile_path",
        help="Путь к JSON-файлу профиля",
    )

    scheduler_run_parser = subparsers.add_parser(
        "scheduler-run",
        help="Запустить задачу Планировщика по профилю",
    )
    scheduler_run_parser.add_argument(
        "profile_path",
        help="Путь к JSON-файлу профиля",
    )

    scheduler_delete_parser = subparsers.add_parser(
        "scheduler-delete",
        help="Удалить задачу Планировщика по профилю",
    )
    scheduler_delete_parser.add_argument(
        "profile_path",
        help="Путь к JSON-файлу профиля",
    )

    return parser


def _load_profile(profile_path: str) -> tuple[ProfileService, BackupProfile]:
    config_store = JsonConfigStore()
    profile_service = ProfileService(config_store)
    profile = profile_service.load_profile(profile_path)
    return profile_service, profile


def _print_task_info(info: ScheduledTaskInfo) -> None:
    if not info.exists:
        print(f"Task not found: {info.task_name}")
        if info.raw_output.strip():
            print(info.raw_output.strip())
        return

    print(f"Task name: {info.task_name}")

    if info.status:
        print(f"Status: {info.status}")

    if info.next_run_time:
        print(f"Next run time: {info.next_run_time}")

    if info.last_result:
        print(f"Last result: {info.last_result}")

    if info.task_to_run:
        print(f"Task to run: {info.task_to_run}")


def run_profile(profile_path: str) -> int:
    _, profile = _load_profile(profile_path)
    backup_runner = BackupRunner()

    result = backup_runner.run_profile(profile)

    print("Backup completed successfully.")
    print(f"Profile: {result.profile_name}")
    print(f"Backup directory: {result.backup_directory}")
    print(f"Run log: {result.run_log_path}")

    if result.created_dump_files:
        print("Created dump files:")
        for file_path in result.created_dump_files:
            print(f"  - {file_path}")

    if result.created_globals_file:
        print(f"Globals file: {result.created_globals_file}")

    return 0


def validate_profile(profile_path: str) -> int:
    profile_service, profile = _load_profile(profile_path)
    profile_service.validate_profile(profile)

    print("Profile is valid.")
    print(f"Profile name: {profile.profile_name}")
    print(f"Databases: {', '.join(profile.postgres.databases)}")
    return 0


def scheduler_create(profile_path: str, run_password: str | None = None) -> int:
    _, profile = _load_profile(profile_path)
    scheduler_service = SchedulerService()

    output = scheduler_service.create_or_update_task(
        profile=profile,
        profile_path=profile_path,
        run_password=run_password,
    )

    print("Scheduler task created/updated successfully.")
    if output:
        print(output)

    info = scheduler_service.query_task(profile)
    _print_task_info(info)
    return 0


def scheduler_query(profile_path: str) -> int:
    _, profile = _load_profile(profile_path)
    scheduler_service = SchedulerService()

    info = scheduler_service.query_task(profile)
    _print_task_info(info)
    return 0 if info.exists else 6


def scheduler_run(profile_path: str) -> int:
    _, profile = _load_profile(profile_path)
    scheduler_service = SchedulerService()

    output = scheduler_service.run_task(profile)
    print("Scheduler task started.")
    if output:
        print(output)
    return 0


def scheduler_delete(profile_path: str) -> int:
    _, profile = _load_profile(profile_path)
    scheduler_service = SchedulerService()

    output = scheduler_service.delete_task(profile)
    print("Scheduler task deleted.")
    if output:
        print(output)
    return 0


def run_gui() -> int:
    from pg_backup_manager.ui.main_window import run_main_window

    return run_main_window()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if not args.command or args.command == "gui":
            return run_gui()

        if args.command == "run-profile":
            return run_profile(args.profile_path)

        if args.command == "validate-profile":
            return validate_profile(args.profile_path)

        if args.command == "scheduler-create":
            return scheduler_create(args.profile_path, args.run_password)

        if args.command == "scheduler-query":
            return scheduler_query(args.profile_path)

        if args.command == "scheduler-run":
            return scheduler_run(args.profile_path)

        if args.command == "scheduler-delete":
            return scheduler_delete(args.profile_path)

        parser.print_help()
        return 1

    except ValidationError as exc:
        print(f"Validation error: {exc}")
        return 2
    except ConfigError as exc:
        print(f"Config error: {exc}")
        return 3
    except BackupExecutionError as exc:
        print(f"Backup execution error: {exc}")
        return 4
    except SchedulerError as exc:
        print(f"Scheduler error: {exc}")
        return 5
    except PgBackupManagerError as exc:
        print(f"Application error: {exc}")
        return 10
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return 99


if __name__ == "__main__":
    raise SystemExit(main())