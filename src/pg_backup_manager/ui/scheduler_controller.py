from __future__ import annotations

from typing import Callable

from tkinter import messagebox

from pg_backup_manager.app.services import SchedulerService
from pg_backup_manager.domain.models import BackupProfile
from pg_backup_manager.infrastructure.scheduler import ScheduledTaskInfo
from pg_backup_manager.shared.errors import SchedulerError, ValidationError
from pg_backup_manager.ui.form_state import MainWindowState


class SchedulerController:
    def __init__(
        self,
        *,
        state: MainWindowState,
        scheduler_service: SchedulerService,
        ensure_profile_saved: Callable[[], tuple[str, BackupProfile]],
        get_current_profile: Callable[[], BackupProfile],
    ) -> None:
        self._state = state
        self._scheduler_service = scheduler_service
        self._ensure_profile_saved = ensure_profile_saved
        self._get_current_profile = get_current_profile

    def create_or_update_task(self) -> None:
        try:
            profile_path, profile = self._ensure_profile_saved()
            run_password = self._state.run_password_var.get().strip() or None

            output = self._scheduler_service.create_or_update_task(
                profile=profile,
                profile_path=profile_path,
                run_password=run_password,
            )
            self._state.run_password_var.set("")

            self._state.set_status("Задача Планировщика создана/обновлена.")
            info = self._scheduler_service.query_task(profile)
            self.update_scheduler_status(info)

            messagebox.showinfo(
                "Планировщик",
                f"Задача успешно создана/обновлена.\n\n{output or 'Команда выполнена успешно.'}",
            )
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except SchedulerError as exc:
            self._state.set_status(f"Ошибка планировщика: {exc}")
            messagebox.showerror("Ошибка планировщика", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def query_task(self) -> None:
        try:
            profile = self._get_current_profile()
            info = self._scheduler_service.query_task(profile)
            self.update_scheduler_status(info)
            self._state.set_status("Статус задачи обновлён.")
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except SchedulerError as exc:
            self._state.set_status(f"Ошибка планировщика: {exc}")
            messagebox.showerror("Ошибка планировщика", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def run_task_now(self) -> None:
        try:
            profile = self._get_current_profile()
            output = self._scheduler_service.run_task(profile)
            self._state.set_status("Задача Планировщика запущена.")
            messagebox.showinfo("Планировщик", output or "Задача успешно запущена.")
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except SchedulerError as exc:
            self._state.set_status(f"Ошибка планировщика: {exc}")
            messagebox.showerror("Ошибка планировщика", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def delete_task(self) -> None:
        try:
            profile = self._get_current_profile()

            if not messagebox.askyesno(
                "Удаление задачи",
                "Удалить задачу Планировщика для текущего профиля?",
            ):
                return

            output = self._scheduler_service.delete_task(profile)
            self._state.scheduler_status_var.set("Задача Планировщика удалена или не существовала.")
            self._state.set_status("Задача Планировщика удалена.")
            messagebox.showinfo("Планировщик", output or "Задача удалена.")
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except SchedulerError as exc:
            self._state.set_status(f"Ошибка планировщика: {exc}")
            messagebox.showerror("Ошибка планировщика", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def update_scheduler_status(self, info: ScheduledTaskInfo) -> None:
        if not info.exists:
            self._state.scheduler_status_var.set(
                f"Задача '{info.task_name}' не найдена.\n"
                "Вероятно, она ещё не была создана или уже удалена."
            )
            return

        lines = [f"Задача: {info.task_name}"]

        if info.status:
            lines.append(f"Состояние: {info.status}")
        if info.next_run_time:
            lines.append(f"Следующий запуск: {info.next_run_time}")
        if info.last_result:
            lines.append(f"Последний результат: {info.last_result}")
        if info.task_to_run:
            lines.append(f"Команда: {info.task_to_run}")

        self._state.scheduler_status_var.set("\n".join(lines))