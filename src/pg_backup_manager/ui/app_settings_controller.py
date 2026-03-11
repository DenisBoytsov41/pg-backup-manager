from __future__ import annotations

from pathlib import Path
from typing import Callable

import tkinter as tk

from pg_backup_manager.app.services import AppSettingsService
from pg_backup_manager.domain.models import AppSettings
from pg_backup_manager.shared.errors import ConfigError
from pg_backup_manager.ui.form_state import MainWindowState


class AppSettingsController:
    def __init__(
        self,
        *,
        window: tk.Tk,
        state: MainWindowState,
        app_settings_service: AppSettingsService,
        app_settings_path: str | Path,
        create_new_profile: Callable[[], None],
        load_profile: Callable[[str], None],
    ) -> None:
        self._window = window
        self._state = state
        self._app_settings_service = app_settings_service
        self._app_settings_path = str(app_settings_path)
        self._create_new_profile = create_new_profile
        self._load_profile = load_profile

        self._dirty_trace_ids: list[tuple[tk.Variable, str]] = []

    def bind_dirty_tracking(self) -> None:
        variables_to_track: list[tk.Variable] = [
            self._state.profile_name_var,
            self._state.host_var,
            self._state.port_var,
            self._state.databases_var,
            self._state.user_var,
            self._state.password_var,
            self._state.pg_dump_path_var,
            self._state.pg_dumpall_path_var,
            self._state.backup_dir_var,
            self._state.retention_days_var,
            self._state.dump_globals_var,
            self._state.naming_pattern_var,
            self._state.main_log_name_var,
            self._state.log_level_var,
            self._state.scheduler_enabled_var,
            self._state.task_name_var,
            self._state.schedule_type_var,
            self._state.start_time_var,
            self._state.days_of_week_var,
            self._state.run_user_var,
            self._state.run_with_highest_privileges_var,
        ]

        self.unbind_dirty_tracking()

        for variable in variables_to_track:
            trace_id = variable.trace_add("write", self._state.mark_dirty)
            self._dirty_trace_ids.append((variable, trace_id))

    def unbind_dirty_tracking(self) -> None:
        for variable, trace_id in self._dirty_trace_ids:
            try:
                variable.trace_remove("write", trace_id)
            except Exception:
                pass
        self._dirty_trace_ids.clear()

    def load_startup(self) -> AppSettings:
        try:
            app_settings = self._app_settings_service.load_settings(self._app_settings_path)
        except ConfigError:
            app_settings = AppSettings()
        except Exception:
            app_settings = AppSettings()

        width = max(app_settings.window_width, 920)
        height = max(app_settings.window_height, 680)
        self._window.geometry(f"{width}x{height}")

        last_profile_path = app_settings.last_profile_path.strip()
        if last_profile_path and Path(last_profile_path).exists():
            try:
                self._load_profile(last_profile_path)
                self._state.set_status("Загружен последний профиль.")
                return app_settings
            except Exception as exc:
                self._state.set_status(f"Не удалось загрузить последний профиль: {exc}")

        self._create_new_profile()
        return app_settings

    def save_app_settings(self, app_settings: AppSettings) -> None:
        app_settings.window_width = self._window.winfo_width()
        app_settings.window_height = self._window.winfo_height()
        app_settings.last_profile_path = self._state.profile_path_var.get().strip()
        self._app_settings_service.save_settings(self._app_settings_path, app_settings)