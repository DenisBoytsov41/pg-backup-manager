from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from pg_backup_manager import __version__
from pg_backup_manager.app.services import AppSettingsService, ProfileService, SchedulerService
from pg_backup_manager.domain.models import AppSettings, BackupProfile, ScheduleType
from pg_backup_manager.infrastructure.backup_runner import BackupExecutionError, BackupRunner
from pg_backup_manager.infrastructure.config_store import JsonConfigStore
from pg_backup_manager.shared.errors import ConfigError, SchedulerError, ValidationError
from pg_backup_manager.shared.paths import get_app_dir, get_default_app_settings_path
from pg_backup_manager.ui.app_settings_controller import AppSettingsController
from pg_backup_manager.ui.backup_controller import BackupController
from pg_backup_manager.ui.entry_menu import EntryContextMenuManager
from pg_backup_manager.ui.file_actions import ask_directory, ask_open_file, open_in_explorer
from pg_backup_manager.ui.form_state import MainWindowState
from pg_backup_manager.ui.profile_controller import ProfileController
from pg_backup_manager.ui.profile_mapper import build_profile_from_state, populate_state_from_profile
from pg_backup_manager.ui.scheduler_controller import SchedulerController


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

        self._build_config_tab(tab_config)
        self._build_postgres_tab(tab_pg)
        self._build_backup_tab(tab_backup)
        self._build_scheduler_tab(tab_scheduler)
        self._build_actions_tab(tab_actions)

        status_bar = ttk.Label(root, textvariable=self._state.status_var, anchor="w")
        status_bar.grid(row=2, column=0, sticky="ew", pady=(8, 0))

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

    def _build_config_tab(self, parent: ttk.Frame) -> None:
        self._add_labeled_entry(parent, 0, "Имя профиля:", self._state.profile_name_var)

        ttk.Label(
            parent,
            text=(
                "Профиль описывает все настройки backup: PostgreSQL, папку backup, "
                "логи и расписание."
            ),
            foreground="#555555",
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_postgres_tab(self, parent: ttk.Frame) -> None:
        self._add_labeled_entry(parent, 0, "Host:", self._state.host_var)
        self._add_labeled_entry(parent, 1, "Port:", self._state.port_var)
        self._add_labeled_entry(parent, 2, "Базы (через запятую):", self._state.databases_var)
        self._add_labeled_entry(parent, 3, "User:", self._state.user_var)
        self._add_labeled_entry(parent, 4, "Password:", self._state.password_var, show="*")

        self._add_labeled_entry(
            parent,
            5,
            "Путь к pg_dump.exe:",
            self._state.pg_dump_path_var,
            button_text="Выбрать...",
            button_command=lambda: self._choose_file(
                self._state.pg_dump_path_var,
                "Выберите pg_dump.exe",
                [("Executable files", "*.exe"), ("All files", "*.*")],
            ),
        )

        self._add_labeled_entry(
            parent,
            6,
            "Путь к pg_dumpall.exe:",
            self._state.pg_dumpall_path_var,
            button_text="Выбрать...",
            button_command=lambda: self._choose_file(
                self._state.pg_dumpall_path_var,
                "Выберите pg_dumpall.exe",
                [("Executable files", "*.exe"), ("All files", "*.*")],
            ),
        )

    def _build_backup_tab(self, parent: ttk.Frame) -> None:
        self._add_labeled_entry(
            parent,
            0,
            "Папка backup:",
            self._state.backup_dir_var,
            button_text="Выбрать...",
            button_command=lambda: self._choose_folder(
                self._state.backup_dir_var,
                "Выберите папку для backup",
            ),
        )
        self._add_labeled_entry(parent, 1, "Хранить дней:", self._state.retention_days_var)
        self._add_labeled_entry(parent, 2, "Шаблон имени:", self._state.naming_pattern_var)
        self._add_labeled_entry(parent, 3, "Имя общего лога:", self._state.main_log_name_var)
        self._add_labeled_entry(parent, 4, "Log level:", self._state.log_level_var)

        ttk.Checkbutton(
            parent,
            text="Выгружать globals (roles/tablespaces)",
            variable=self._state.dump_globals_var,
        ).grid(row=5, column=1, sticky="w", pady=4)

        ttk.Label(
            parent,
            text=(
                "Шаблон имени может использовать: {database}, {timestamp}, {profile}. "
                "Обязательны {database} и {timestamp}."
            ),
            foreground="#555555",
            wraplength=780,
            justify="left",
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Label(
            parent,
            text="При значении 0 автоочистка старых .backup/.log/.sql файлов отключается.",
            foreground="#555555",
            wraplength=780,
            justify="left",
        ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(6, 0))

        ttk.Label(
            parent,
            text="Если включена выгрузка globals, должен быть указан путь к pg_dumpall.exe.",
            foreground="#555555",
            wraplength=780,
            justify="left",
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def _build_scheduler_tab(self, parent: ttk.Frame) -> None:
        ttk.Checkbutton(
            parent,
            text="Включить планировщик для профиля",
            variable=self._state.scheduler_enabled_var,
        ).grid(row=0, column=1, sticky="w", pady=4)

        self._add_labeled_entry(parent, 1, "Имя задачи:", self._state.task_name_var)

        self._add_labeled_combobox(
            parent,
            2,
            "Тип расписания:",
            self._state.schedule_type_var,
            [item.value for item in ScheduleType],
        )

        self._add_labeled_entry(parent, 3, "Время запуска (HH:MM):", self._state.start_time_var)
        self._days_of_week_entry = self._add_labeled_entry(
            parent,
            4,
            "Дни недели (через запятую):",
            self._state.days_of_week_var,
        )
        self._add_labeled_entry(parent, 5, "Пользователь запуска:", self._state.run_user_var)
        self._add_labeled_entry(
            parent,
            6,
            "Пароль запуска (не сохраняется):",
            self._state.run_password_var,
            show="*",
        )

        ttk.Checkbutton(
            parent,
            text="Запускать с наивысшими правами",
            variable=self._state.run_with_highest_privileges_var,
        ).grid(row=7, column=1, sticky="w", pady=4)

        ttk.Label(
            parent,
            text=(
                "Если планировщик включён, имя задачи обязательно, а тип расписания "
                "не должен быть disabled."
            ),
            foreground="#555555",
            wraplength=780,
            justify="left",
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(6, 8))

        scheduler_actions = ttk.LabelFrame(parent, text="Управление задачей", padding=10)
        scheduler_actions.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        scheduler_actions.columnconfigure(0, weight=1)

        self._scheduler_create_button = ttk.Button(
            scheduler_actions,
            text="Создать / обновить задачу",
            command=self._scheduler_controller.create_or_update_task,
        )
        self._scheduler_create_button.grid(row=0, column=0, sticky="w", padx=4, pady=4)

        ttk.Button(
            scheduler_actions,
            text="Проверить задачу",
            command=self._scheduler_controller.query_task,
        ).grid(row=1, column=0, sticky="w", padx=4, pady=4)

        ttk.Button(
            scheduler_actions,
            text="Запустить задачу сейчас",
            command=self._scheduler_controller.run_task_now,
        ).grid(row=2, column=0, sticky="w", padx=4, pady=4)

        ttk.Button(
            scheduler_actions,
            text="Удалить задачу",
            command=self._scheduler_controller.delete_task,
        ).grid(row=3, column=0, sticky="w", padx=4, pady=4)

        ttk.Label(
            scheduler_actions,
            textvariable=self._state.scheduler_status_var,
            justify="left",
            wraplength=760,
            foreground="#333333",
        ).grid(row=4, column=0, sticky="w", padx=4, pady=(10, 4))

    def _build_actions_tab(self, parent: ttk.Frame) -> None:
        actions = ttk.LabelFrame(parent, text="Действия", padding=10)
        actions.grid(row=0, column=0, columnspan=2, sticky="ew")
        actions.columnconfigure(0, weight=1)

        ttk.Button(actions, text="Проверить профиль", command=self._backup_controller.validate_profile).grid(
            row=0, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Button(actions, text="Тестовый backup сейчас", command=self._backup_controller.run_test_backup).grid(
            row=1, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Button(actions, text="Открыть папку backup", command=self._backup_controller.open_backup_folder).grid(
            row=2, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Button(actions, text="Открыть папку приложения", command=self._open_app_folder).grid(
            row=3, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Button(actions, text="Закрыть", command=self._on_close).grid(
            row=4, column=0, sticky="w", padx=4, pady=(12, 4)
        )

    def _create_entry(
        self,
        parent: ttk.Widget,
        variable: tk.StringVar,
        show: str | None = None,
    ) -> ttk.Entry:
        if show is None:
            entry = ttk.Entry(parent, textvariable=variable)
        else:
            entry = ttk.Entry(parent, textvariable=variable, show=show)

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

    # -------------------------------------------------------------------------
    # State mapping
    # -------------------------------------------------------------------------

    def _get_current_profile(self) -> BackupProfile:
        return build_profile_from_state(self._state)

    def _apply_profile(self, profile: BackupProfile) -> None:
        populate_state_from_profile(self._state, profile)
        self._update_scheduler_field_states()

    # -------------------------------------------------------------------------
    # Dynamic UI state
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # File/folder actions
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Startup / shutdown
    # -------------------------------------------------------------------------

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