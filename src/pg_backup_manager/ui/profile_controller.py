from __future__ import annotations

from pathlib import Path
from typing import Callable

from tkinter import messagebox

from pg_backup_manager.app.services import AppSettingsService, ProfileService
from pg_backup_manager.domain.models import AppSettings, BackupProfile
from pg_backup_manager.shared.errors import ConfigError, ValidationError
from pg_backup_manager.ui.file_actions import ask_open_file, ask_save_file, open_in_explorer
from pg_backup_manager.ui.form_state import MainWindowState


class ProfileController:
    def __init__(
        self,
        *,
        state: MainWindowState,
        app_dir: str | Path,
        profile_service: ProfileService,
        app_settings_service: AppSettingsService,
        app_settings: AppSettings,
        get_current_profile: Callable[[], BackupProfile],
        apply_profile: Callable[[BackupProfile], None],
    ) -> None:
        self._state = state
        self._app_dir = Path(app_dir)
        self._profile_service = profile_service
        self._app_settings_service = app_settings_service
        self._app_settings = app_settings
        self._get_current_profile = get_current_profile
        self._apply_profile = apply_profile

    def set_app_settings(self, app_settings: AppSettings) -> None:
        self._app_settings = app_settings

    def new_profile(self) -> None:
        profile = self._profile_service.create_default_profile()
        self._apply_profile(profile)
        self._state.profile_path_var.set("")
        self._state.reset_scheduler_status()
        self._state.set_status("Создан новый профиль.")
        self._state.mark_clean()

    def browse_profile(self) -> None:
        path = ask_open_file(
            title="Выберите профиль backup",
            current_value=self._state.profile_path_var.get(),
            fallback_dir=self._app_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._state.profile_path_var.set(path)

    def load_profile_from_current_path(self) -> None:
        profile_path = self._state.profile_path_var.get().strip()
        if not profile_path:
            messagebox.showwarning("Нет пути", "Укажи путь к JSON-файлу профиля.")
            return

        self.load_profile(profile_path)

    def load_profile(self, profile_path: str) -> None:
        try:
            profile = self._profile_service.load_profile(profile_path)
            self._apply_profile(profile)
            self._state.profile_path_var.set(profile_path)
            self._app_settings = self._app_settings_service.register_recent_profile(
                self._app_settings,
                profile_path,
            )
            self._state.reset_scheduler_status()
            self._state.set_status(f"Профиль загружен: {profile_path}")
            self._state.mark_clean()
        except ConfigError as exc:
            self._state.set_status(f"Ошибка конфигурации: {exc}")
            messagebox.showerror("Ошибка конфигурации", str(exc))
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def save_profile(self) -> None:
        profile_path = self._state.profile_path_var.get().strip()
        if not profile_path:
            self.save_profile_as()
            return

        try:
            profile = self._get_current_profile()
            self._profile_service.save_profile(profile_path, profile)
            self._app_settings = self._app_settings_service.register_recent_profile(
                self._app_settings,
                profile_path,
            )
            self._state.set_status(f"Профиль сохранён: {profile_path}")
            self._state.mark_clean()
            messagebox.showinfo("Сохранено", f"Профиль сохранён:\n{profile_path}")
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except ConfigError as exc:
            self._state.set_status(f"Ошибка конфигурации: {exc}")
            messagebox.showerror("Ошибка конфигурации", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def save_profile_as(self) -> None:
        try:
            profile = self._get_current_profile()
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
            return
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))
            return

        current_path = self._state.profile_path_var.get().strip()
        initialfile = self._profile_service.get_profile_file_name(profile)

        path = ask_save_file(
            title="Сохранить профиль backup как",
            current_value=current_path,
            fallback_dir=self._app_dir,
            initialfile=initialfile,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            self._profile_service.save_profile(path, profile)
            self._state.profile_path_var.set(path)
            self._app_settings = self._app_settings_service.register_recent_profile(
                self._app_settings,
                path,
            )
            self._state.set_status(f"Профиль сохранён: {path}")
            self._state.mark_clean()
            messagebox.showinfo("Сохранено", f"Профиль сохранён:\n{path}")
        except ValidationError as exc:
            self._state.set_status(f"Ошибка проверки: {exc}")
            messagebox.showerror("Ошибка проверки", str(exc))
        except ConfigError as exc:
            self._state.set_status(f"Ошибка конфигурации: {exc}")
            messagebox.showerror("Ошибка конфигурации", str(exc))
        except Exception as exc:
            self._state.set_status(f"Неожиданная ошибка: {exc}")
            messagebox.showerror("Неожиданная ошибка", str(exc))

    def ensure_profile_saved(self) -> tuple[str, BackupProfile]:
        profile = self._get_current_profile()
        profile_path = self._state.profile_path_var.get().strip()

        if not profile_path:
            initialfile = self._profile_service.get_profile_file_name(profile)
            profile_path = ask_save_file(
                title="Сохранить профиль backup как",
                current_value="",
                fallback_dir=self._app_dir,
                initialfile=initialfile,
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )

            if not profile_path:
                raise ValidationError("Операция отменена: профиль должен быть сохранён.")

            self._state.profile_path_var.set(profile_path)

        self._profile_service.save_profile(profile_path, profile)
        self._app_settings = self._app_settings_service.register_recent_profile(
            self._app_settings,
            profile_path,
        )
        self._state.mark_clean()
        return profile_path, profile

    def open_profile_folder(self) -> None:
        profile_path = self._state.profile_path_var.get().strip()
        if not profile_path:
            messagebox.showwarning("Нет пути", "Не указан путь к профилю.")
            return

        open_in_explorer(Path(profile_path).parent)