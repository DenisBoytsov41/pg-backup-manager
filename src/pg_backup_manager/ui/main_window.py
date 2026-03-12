from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from pg_backup_manager import __version__
from pg_backup_manager.app.services import AppSettingsService, ProfileService, SchedulerService
from pg_backup_manager.domain.models import AppSettings, BackupProfile, ScheduleType
from pg_backup_manager.infrastructure.backup_runner import BackupRunner
from pg_backup_manager.infrastructure.config_store import JsonConfigStore
from pg_backup_manager.shared.errors import (
    BackupExecutionError,
    ConfigError,
    SchedulerError,
    ValidationError,
)
from pg_backup_manager.shared.paths import get_app_dir, get_default_app_settings_path
from pg_backup_manager.ui.app_settings_controller import AppSettingsController
from pg_backup_manager.ui.backup_controller import BackupController
from pg_backup_manager.ui.entry_menu import EntryContextMenuManager
from pg_backup_manager.ui.file_actions import ask_directory, ask_open_file, open_in_explorer
from pg_backup_manager.ui.form_state import MainWindowState
from pg_backup_manager.ui.profile_controller import ProfileController
from pg_backup_manager.ui.profile_mapper import build_profile_from_state, populate_state_from_profile
from pg_backup_manager.ui.scheduler_controller import SchedulerController
from pg_backup_manager.ui.tabs.actions_tab import build_actions_tab
from pg_backup_manager.ui.tabs.backup_tab import build_backup_tab
from pg_backup_manager.ui.tabs.config_tab import build_config_tab
from pg_backup_manager.ui.tabs.postgres_tab import build_postgres_tab
from pg_backup_manager.ui.tabs.scheduler_tab import build_scheduler_tab


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title(f"PG Backup Manager {__version__}")
        self.geometry("1020x760")
        self.minsize(920, 680)

        self._config_store = JsonConfigStore()
        self._profile_service = ProfileService(self._config_store)
        self._app_settings_service = AppSettingsService(self._config_store)
        self._backup_runner = BackupRunner()
        self._scheduler_service = SchedulerService()

        self._app_dir = get_app_dir()
        self._app_settings_path = get_default_app_settings_path()
        self._app_settings = AppSettings()

        self._state = MainWindowState.create(self)
        self._entry_menu_manager = EntryContextMenuManager(self)

        self._days_of_week_entry: ttk.Entry | None = None
        self._scheduler_create_button: ttk.Button | None = None

        self._create_controllers()
        self._build_ui()
        self._bind_dynamic_state()
        self._load_startup()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_controllers(self) -> None:
        self._profile_controller = ProfileController(
            state=self._state,
            app_dir=self._app_dir,
            profile_service=self._profile_service,
            app_settings_service=self._app_settings_service,
            app_settings=self._app_settings,
            get_current_profile=self._get_current_profile,
            apply_profile=self._apply_profile,
        )

        self._backup_controller = BackupController(
            state=self._state,
            profile_service=self._profile_service,
            backup_runner=self._backup_runner,
            get_current_profile=self._get_current_profile,
        )

        self._scheduler_controller = SchedulerController(
            state=self._state,
            scheduler_service=self._scheduler_service,
            ensure_profile_saved=self._profile_controller.ensure_profile_saved,
            get_current_profile=self._get_current_profile,
        )

        self._app_settings_controller = AppSettingsController(
            window=self,
            state=self._state,
            app_settings_service=self._app_settings_service,
            app_settings_path=self._app_settings_path,
            create_new_profile=self._profile_controller.new_profile,
            load_profile=self._profile_controller.load_profile,
        )

        self._app_settings_controller.bind_dirty_tracking()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, padding=10)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        self._build_profile_top_panel(root)

        notebook = ttk.Notebook(root)
        notebook.grid(row=1, column=0, sticky="nsew")
        notebook.enable_traversal()

        tab_config = ttk.Frame(notebook, padding=12)
        tab_pg = ttk.Frame(notebook, padding=12)
        tab_backup = ttk.Frame(notebook, padding=12)
        tab_scheduler = ttk.Frame(notebook, padding=12)
        tab_actions = ttk.Frame(notebook, padding=12)

        for tab in (tab_config, tab_pg, tab_backup, tab_scheduler, tab_actions):
            tab.columnconfigure(1, weight=1)

        notebook.add(tab_config, text="Конфиг")
        notebook.add(tab_pg, text="PostgreSQL")
        notebook.add(tab_backup, text="Backup")
        notebook.add(tab_scheduler, text="Планировщик")
        notebook.add(tab_actions, text="Действия")

        build_config_tab(
            parent=tab_config,
            state=self._state,
            add_labeled_entry=self._add_labeled_entry,
        )

        build_postgres_tab(
            parent=tab_pg,
            state=self._state,
            add_labeled_entry=self._add_labeled_entry,
            choose_file=self._choose_file,
        )

        build_backup_tab(
            parent=tab_backup,
            state=self._state,
            add_labeled_entry=self._add_labeled_entry,
            choose_folder=self._choose_folder,
        )

        self._days_of_week_entry, self._scheduler_create_button = build_scheduler_tab(
            parent=tab_scheduler,
            state=self._state,
            add_labeled_entry=self._add_labeled_entry,
            add_labeled_combobox=self._add_labeled_combobox,
            create_or_update_task=self._scheduler_controller.create_or_update_task,
            query_task=self._scheduler_controller.query_task,
            run_task_now=self._scheduler_controller.run_task_now,
            delete_task=self._scheduler_controller.delete_task,
        )

        build_actions_tab(
            parent=tab_actions,
            validate_profile=self._backup_controller.validate_profile,
            run_test_backup=self._backup_controller.run_test_backup,
            open_backup_folder=self._backup_controller.open_backup_folder,
            open_app_folder=self._open_app_folder,
            close_window=self._on_close,
        )

        ttk.Label(root, textvariable=self._state.status_var, anchor="w").grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

    def _build_profile_top_panel(self, parent: ttk.Frame) -> None:
        top = ttk.LabelFrame(parent, text="Профиль", padding=10)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Путь к профилю:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self._create_entry(top, self._state.profile_path_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Button(top, text="Открыть...", command=self._profile_controller.browse_profile).grid(
            row=0, column=2, padx=4, pady=4
        )
        ttk.Button(top, text="Загрузить", command=self._profile_controller.load_profile_from_current_path).grid(
            row=0, column=3, padx=4, pady=4
        )
        ttk.Button(top, text="Новый", command=self._profile_controller.new_profile).grid(
            row=1, column=0, padx=4, pady=4, sticky="w"
        )
        ttk.Button(top, text="Сохранить", command=self._profile_controller.save_profile).grid(
            row=1, column=1, padx=4, pady=4, sticky="w"
        )
        ttk.Button(top, text="Сохранить как...", command=self._profile_controller.save_profile_as).grid(
            row=1, column=2, padx=4, pady=4, sticky="w"
        )
        ttk.Button(top, text="Открыть папку профиля", command=self._profile_controller.open_profile_folder).grid(
            row=1, column=3, padx=4, pady=4, sticky="w"
        )

    def _create_entry(
        self,
        parent: ttk.Widget,
        variable: tk.StringVar,
        show: str | None = None,
    ) -> ttk.Entry:
        entry = ttk.Entry(parent, textvariable=variable) if show is None else ttk.Entry(
            parent,
            textvariable=variable,
            show=show,
        )
        self._entry_menu_manager.attach(entry)
        return entry

    def _add_labeled_entry(
        self,
        parent: ttk.Widget,
        row: int,
        label: str,
        variable: tk.StringVar,
        button_text: str | None = None,
        button_command: Callable[[], None] | None = None,
        show: str | None = None,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)

        entry = self._create_entry(parent, variable, show=show)
        entry.grid(row=row, column=1, sticky="ew", pady=4)

        if button_text and button_command:
            ttk.Button(parent, text=button_text, command=button_command).grid(
                row=row,
                column=2,
                padx=4,
                pady=4,
            )

        return entry

    def _add_labeled_combobox(
        self,
        parent: ttk.Widget,
        row: int,
        label: str,
        variable: tk.StringVar,
        values: list[str],
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        combobox = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        combobox.grid(row=row, column=1, sticky="ew", pady=4)
        return combobox

    def _get_current_profile(self) -> BackupProfile:
        return build_profile_from_state(self._state)

    def _apply_profile(self, profile: BackupProfile) -> None:
        populate_state_from_profile(self._state, profile)
        self._update_scheduler_field_states()

    def _bind_dynamic_state(self) -> None:
        self._state.scheduler_enabled_var.trace_add("write", self._on_scheduler_state_changed)
        self._state.schedule_type_var.trace_add("write", self._on_scheduler_state_changed)
        self._update_scheduler_field_states()

    def _on_scheduler_state_changed(self, *_args: object) -> None:
        self._update_scheduler_field_states()

    def _update_scheduler_field_states(self) -> None:
        scheduler_enabled = bool(self._state.scheduler_enabled_var.get())
        schedule_type = self._state.schedule_type_var.get().strip()

        if self._days_of_week_entry is not None:
            if scheduler_enabled and schedule_type == ScheduleType.WEEKLY.value:
                self._days_of_week_entry.state(["!disabled"])
            else:
                self._days_of_week_entry.state(["disabled"])

        if self._scheduler_create_button is not None:
            if scheduler_enabled:
                self._scheduler_create_button.state(["!disabled"])
            else:
                self._scheduler_create_button.state(["disabled"])

    def _choose_file(
        self,
        variable: tk.StringVar,
        title: str,
        filetypes: list[tuple[str, str]],
    ) -> None:
        path = ask_open_file(
            title=title,
            current_value=variable.get(),
            fallback_dir=self._app_dir,
            filetypes=filetypes,
        )
        if path:
            variable.set(path)

    def _choose_folder(self, variable: tk.StringVar, title: str) -> None:
        path = ask_directory(
            title=title,
            current_value=variable.get(),
            fallback_dir=self._app_dir,
        )
        if path:
            variable.set(path)

    def _open_app_folder(self) -> None:
        open_in_explorer(self._app_dir)

    def _load_startup(self) -> None:
        self._app_settings = self._app_settings_controller.load_startup()
        self._profile_controller.set_app_settings(self._app_settings)

        current_profile_path = self._state.profile_path_var.get().strip()
        if current_profile_path:
            self._app_settings = self._app_settings_service.register_recent_profile(
                self._app_settings,
                current_profile_path,
            )
            self._profile_controller.set_app_settings(self._app_settings)

        self._state.mark_clean()
        self._update_scheduler_field_states()

    def _on_close(self) -> None:
        if self._state.dirty_var.get():
            answer = messagebox.askyesnocancel(
                "Несохранённые изменения",
                "Есть несохранённые изменения. Сохранить профиль перед выходом?",
            )

            if answer is None:
                return

            if answer:
                self._profile_controller.save_profile()
                if self._state.dirty_var.get():
                    return

        try:
            self._app_settings_controller.save_app_settings(self._app_settings)
        except Exception:
            pass

        self.destroy()


def run_main_window() -> int:
    try:
        app = MainWindow()
        app.mainloop()
        return 0
    except ValidationError as exc:
        messagebox.showerror("Ошибка проверки", str(exc))
        return 2
    except ConfigError as exc:
        messagebox.showerror("Ошибка конфигурации", str(exc))
        return 3
    except BackupExecutionError as exc:
        messagebox.showerror("Ошибка backup", str(exc))
        return 4
    except SchedulerError as exc:
        messagebox.showerror("Ошибка планировщика", str(exc))
        return 5
    except Exception as exc:
        messagebox.showerror("Неожиданная ошибка", str(exc))
        return 99