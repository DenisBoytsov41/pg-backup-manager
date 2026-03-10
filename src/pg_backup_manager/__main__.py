from __future__ import annotations

import argparse
from pathlib import Path

from pg_backup_manager.app.services import ProfileService
from pg_backup_manager.infrastructure.backup_runner import BackupRunner
from pg_backup_manager.infrastructure.config_store import JsonConfigStore
from pg_backup_manager.shared.errors import (
    BackupExecutionError,
    ConfigError,
    PgBackupManagerError,
    ValidationError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pg_backup_manager",
        description="PG Backup Manager CLI",
    )

    subparsers = parser.add_subparsers(dest="command")

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

    return parser


def run_profile(profile_path: str) -> int:
    config_store = JsonConfigStore()
    profile_service = ProfileService(config_store)
    backup_runner = BackupRunner()

    profile = profile_service.load_profile(profile_path)
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
    config_store = JsonConfigStore()
    profile_service = ProfileService(config_store)

    profile = profile_service.load_profile(profile_path)
    profile_service.save_profile(profile_path, profile)

    print("Profile is valid.")
    print(f"Profile name: {profile.profile_name}")
    print(f"Databases: {', '.join(profile.postgres.databases)}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        print("PG Backup Manager bootstrap")
        parser.print_help()
        return 0

    try:
        if args.command == "run-profile":
            return run_profile(args.profile_path)

        if args.command == "validate-profile":
            return validate_profile(args.profile_path)

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
    except PgBackupManagerError as exc:
        print(f"Application error: {exc}")
        return 10
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return 99


if __name__ == "__main__":
    raise SystemExit(main())