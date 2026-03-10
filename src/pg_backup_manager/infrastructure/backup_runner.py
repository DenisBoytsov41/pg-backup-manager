from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pg_backup_manager.domain.models import BackupProfile
from pg_backup_manager.domain.validators import validate_existing_executable, validate_profile
from pg_backup_manager.infrastructure.logging_service import LoggingService
from pg_backup_manager.shared.errors import BackupExecutionError
from pg_backup_manager.shared.paths import (
    build_dump_file_name,
    build_globals_file_name,
    build_run_log_name,
    ensure_directory,
    normalize_path,
)


@dataclass(slots=True)
class BackupRunResult:
    success: bool
    profile_name: str
    databases: list[str]
    backup_directory: str
    created_dump_files: list[str]
    created_globals_file: str | None
    run_log_path: str
    message: str
    exit_code: int = 0


class BackupRunner:
    def run_profile(self, profile: BackupProfile) -> BackupRunResult:
        validate_profile(profile)
        validate_existing_executable(profile.postgres.pg_dump_path, "pg_dump.exe")

        backup_dir = ensure_directory(normalize_path(profile.backup.backup_dir))
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_log_name = build_run_log_name(profile.profile_name, timestamp)
        logger = LoggingService(backup_dir, profile.logging.main_log_name)
        run_log_path = backup_dir / run_log_name

        logger.write_main_log(f"START: Запуск backup для профиля '{profile.profile_name}'.")

        created_dump_files: list[str] = []
        created_globals_file: str | None = None

        previous_password = os.environ.get("PGPASSWORD")

        try:
            if profile.postgres.password.strip():
                os.environ["PGPASSWORD"] = profile.postgres.password
            else:
                os.environ.pop("PGPASSWORD", None)

            for database_name in profile.postgres.databases:
                dump_file_name = build_dump_file_name(database_name, timestamp)
                dump_path = backup_dir / dump_file_name

                args = [
                    profile.postgres.pg_dump_path,
                    "-h",
                    profile.postgres.host,
                    "-p",
                    str(profile.postgres.port),
                    "-U",
                    profile.postgres.user,
                    "--format=custom",
                    "--verbose",
                    "--file",
                    str(dump_path),
                    "--no-password",
                    database_name,
                ]

                result = subprocess.run(args, capture_output=True)

                stdout_text = self._decode_bytes(result.stdout)
                stderr_text = self._decode_bytes(result.stderr)
                output_text = self._combine_output(stdout_text, stderr_text)

                logger.append_to_run_log(run_log_path, f"Backup базы '{database_name}'")
                logger.append_to_run_log(
                    run_log_path,
                    output_text.strip() or "Нет вывода процесса.",
                )

                if result.returncode != 0:
                    if dump_path.exists():
                        dump_path.unlink(missing_ok=True)

                    logger.write_main_log(
                        f"Ошибка при создании backup базы '{database_name}'.",
                        level="ERROR",
                    )
                    raise BackupExecutionError(
                        f"Ошибка при создании backup базы '{database_name}'. "
                        f"Смотрите run-log: {run_log_path}"
                    )

                created_dump_files.append(str(dump_path))

            if profile.backup.dump_globals and profile.postgres.pg_dumpall_path.strip():
                validate_existing_executable(profile.postgres.pg_dumpall_path, "pg_dumpall.exe")

                globals_file_name = build_globals_file_name(timestamp)
                globals_path = backup_dir / globals_file_name

                globals_args = [
                    profile.postgres.pg_dumpall_path,
                    "-h",
                    profile.postgres.host,
                    "-p",
                    str(profile.postgres.port),
                    "-U",
                    profile.postgres.user,
                    "--globals-only",
                    "--no-password",
                ]

                result = subprocess.run(globals_args, capture_output=True)

                stdout_text = self._decode_bytes(result.stdout)
                stderr_text = self._decode_bytes(result.stderr)

                logger.append_to_run_log(run_log_path, "Выгрузка globals")
                logger.append_to_run_log(
                    run_log_path,
                    stderr_text.strip() or "Нет служебного вывода процесса.",
                )

                if result.returncode == 0:
                    globals_path.write_bytes(result.stdout or b"")
                    created_globals_file = str(globals_path)
                    logger.write_main_log(
                        f"Globals сохранены в '{globals_path.name}'.",
                        level="INFO",
                    )
                else:
                    logger.write_main_log(
                        "Не удалось выгрузить globals.",
                        level="WARNING",
                    )

            self._cleanup_old_files(
                backup_dir=backup_dir,
                retention_days=profile.backup.retention_days,
                main_log_name=profile.logging.main_log_name,
            )

            success_message = "Резервное копирование выполнено успешно."
            logger.write_main_log(success_message, level="INFO")

            return BackupRunResult(
                success=True,
                profile_name=profile.profile_name,
                databases=profile.postgres.databases,
                backup_directory=str(backup_dir),
                created_dump_files=created_dump_files,
                created_globals_file=created_globals_file,
                run_log_path=str(run_log_path),
                message=success_message,
                exit_code=0,
            )

        except BackupExecutionError:
            raise
        except Exception as exc:
            logger.write_main_log(str(exc), level="ERROR")
            raise BackupExecutionError(str(exc)) from exc
        finally:
            if previous_password is not None:
                os.environ["PGPASSWORD"] = previous_password
            else:
                os.environ.pop("PGPASSWORD", None)

    def _cleanup_old_files(self, backup_dir: Path, retention_days: int, main_log_name: str) -> None:
        if retention_days <= 0:
            return

        border = datetime.now().timestamp() - retention_days * 24 * 60 * 60

        for file_path in backup_dir.iterdir():
            if not file_path.is_file():
                continue

            if file_path.name == main_log_name:
                continue

            if file_path.suffix.lower() not in {".backup", ".log", ".sql"}:
                continue

            if file_path.stat().st_mtime < border:
                file_path.unlink(missing_ok=True)

    def _decode_bytes(self, data: bytes | None) -> str:
        if not data:
            return ""

        for encoding in ("cp866", "cp1251", "utf-8"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

        return data.decode("utf-8", errors="replace")

    def _combine_output(self, stdout_text: str, stderr_text: str) -> str:
        parts = []
        if stdout_text.strip():
            parts.append(stdout_text.strip())
        if stderr_text.strip():
            parts.append(stderr_text.strip())
        return "\n".join(parts)