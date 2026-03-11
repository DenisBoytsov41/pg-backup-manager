from __future__ import annotations

from typing import Callable

from tkinter import messagebox

from pg_backup_manager.app.services import ProfileService
from pg_backup_manager.domain.models import BackupProfile
from pg_backup_manager.infrastructure.backup_runner import BackupRunResult, BackupRunner
from pg_backup_manager.shared.errors import BackupExecutionError, ValidationError
from pg_backup_manager.ui.file_actions import open_in_explorer
from pg_backup_manager.ui.form_state import MainWindowState


class BackupController:
    def __init__(
        self,
        *,
        state: MainWindowState,
        profile_service: ProfileService,
        backup_runner: BackupRunner,
        get_current_profile: Callable[[], BackupProfile],
    ) -> None:
        self._state = state
        self._profile_service = profile_service
        self._backup_runner = backup_runner
        self._get_current_profile = get_current_profile

    def validate_profile(self) -> None:
        try:
            profile = self._get_current_profile()
            self._profile_service.validate_profile(profile)
            self._state.set_status("Профиль корректен.")
            messagebox.showinfo("Проверка", "Профиль корректен.")
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def run_test_backup(self) -> None:
        try:
            profile = self._get_current_profile()
            result = self._backup_runner.run_profile(profile)
            self.show_backup_result(result)
            self._state.set_status("Тестовый backup выполнен успешно.")
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except BackupExecutionError as exc:
            self._state.set_status(f"Ошибка backup: {exc}")
            messagebox.showerror("Ошибка backup", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def show_backup_result(self, result: BackupRunResult) -> None:
        lines = [
            "Резервное копирование выполнено успешно.",
            "",
            f"Профиль: {result.profile_name}",
            f"Папка backup: {result.backup_directory}",
            f"Run log: {result.run_log_path}",
        ]

        if result.created_dump_files:
            lines.append("")
            lines.append("Созданные dump-файлы:")
            for file_path in result.created_dump_files:
                lines.append(f" - {file_path}")

        if result.created_globals_file:
            lines.append("")
            lines.append(f"Globals: {result.created_globals_file}")

        messagebox.showinfo("Успех", "\n".join(lines))

    def open_backup_folder(self) -> None:
        backup_dir = self._state.backup_dir_var.get().strip()
        if not backup_dir:
            messagebox.showwarning("Нет пути", "Не указана папка backup.")
            return

        open_in_explorer(backup_dir)