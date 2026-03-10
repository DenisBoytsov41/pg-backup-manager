from __future__ import annotations

import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, cast

from pg_backup_manager.app.services import AppSettingsService, ProfileService, SchedulerService
from pg_backup_manager.domain.models import (
    AppSettings,
    BackupProfile,
    BackupSettings,
    LoggingSettings,
    PostgresSettings,
    ScheduleType,
    SchedulerSettings,
)
from pg_backup_manager.infrastructure.backup_runner import BackupRunResult, BackupRunner
from pg_backup_manager.infrastructure.config_store import JsonConfigStore
from pg_backup_manager.infrastructure.scheduler import ScheduledTaskInfo
from pg_backup_manager.shared.errors import (
    BackupExecutionError,
    ConfigError,
    SchedulerError,
    ValidationError,
)
from pg_backup_manager.shared.paths import get_app_dir, get_default_app_settings_path

EntryWidget = tk.Entry | ttk.Entry


def open_in_explorer(path: str) -> None:
    if not path:
        return

    normalized = os.path.normpath(path)
    if not os.path.exists(normalized):
        messagebox.showwarning("Путь не найден", f"Путь не существует:\n{normalized}")
        return

    if os.name == "nt":
        os.startfile(normalized)
    elif os.name == "posix":
        subprocess.Popen(["xdg-open", normalized])
    else:
        messagebox.showinfo("Путь", normalized)


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("PG Backup Manager")
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

        self._status_var = tk.StringVar(value="Готово.")
        self._scheduler_status_var = tk.StringVar(value="Статус задачи не запрошен.")
        self._profile_path_var = tk.StringVar()
        self._profile_name_var = tk.StringVar()

        self._host_var = tk.StringVar()
        self._port_var = tk.StringVar(value="5432")
        self._databases_var = tk.StringVar()
        self._user_var = tk.StringVar(value="postgres")
        self._password_var = tk.StringVar()
        self._pg_dump_path_var = tk.StringVar()
        self._pg_dumpall_path_var = tk.StringVar()

        self._backup_dir_var = tk.StringVar()
        self._retention_days_var = tk.StringVar(value="30")
        self._dump_globals_var = tk.BooleanVar(value=True)
        self._naming_pattern_var = tk.StringVar(value="{database}_{timestamp}")

        self._main_log_name_var = tk.StringVar(value="backup.log")
        self._log_level_var = tk.StringVar(value="INFO")

        self._scheduler_enabled_var = tk.BooleanVar(value=False)
        self._task_name_var = tk.StringVar()
        self._schedule_type_var = tk.StringVar(value=ScheduleType.DISABLED.value)
        self._start_time_var = tk.StringVar(value="02:00")
        self._days_of_week_var = tk.StringVar()
        self._run_user_var = tk.StringVar()
        self._run_password_var = tk.StringVar()
        self._run_with_highest_privileges_var = tk.BooleanVar(value=False)

        self._entry_menu: tk.Menu | None = None

        self._build_ui()
        self._create_context_menu()
        self._load_startup()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, padding=10)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        top = ttk.LabelFrame(root, text="Профиль", padding=10)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Путь к профилю:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self._create_entry(top, self._profile_path_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Button(top, text="Открыть...", command=self._browse_profile).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(top, text="Загрузить", command=self._load_profile_from_current_path).grid(
            row=0, column=3, padx=4, pady=4
        )
        ttk.Button(top, text="Новый", command=self._new_profile).grid(row=1, column=0, padx=4, pady=4, sticky="w")
        ttk.Button(top, text="Сохранить", command=self._save_profile).grid(
            row=1, column=1, padx=4, pady=4, sticky="w"
        )
        ttk.Button(top, text="Сохранить как...", command=self._save_profile_as).grid(
            row=1, column=2, padx=4, pady=4, sticky="w"
        )
        ttk.Button(top, text="Открыть папку профиля", command=self._open_profile_folder).grid(
            row=1, column=3, padx=4, pady=4, sticky="w"
        )

        notebook = ttk.Notebook(root)
        notebook.grid(row=1, column=0, sticky="nsew")

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

        self._add_labeled_entry(tab_config, 0, "Имя профиля:", self._profile_name_var)
        ttk.Label(
            tab_config,
            text="Профиль описывает все настройки backup: PostgreSQL, папку backup, логи и расписание.",
            foreground="#555555",
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self._add_labeled_entry(tab_pg, 0, "Host:", self._host_var)
        self._add_labeled_entry(tab_pg, 1, "Port:", self._port_var)
        self._add_labeled_entry(tab_pg, 2, "Базы (через запятую):", self._databases_var)
        self._add_labeled_entry(tab_pg, 3, "User:", self._user_var)
        self._add_labeled_entry(tab_pg, 4, "Password:", self._password_var, show="*")
        self._add_labeled_entry(
            tab_pg,
            5,
            "Путь к pg_dump.exe:",
            self._pg_dump_path_var,
            button_text="Выбрать...",
            button_command=lambda: self._choose_file(
                self._pg_dump_path_var,
                "Выберите pg_dump.exe",
                [("Executable files", "*.exe"), ("All files", "*.*")],
            ),
        )
        self._add_labeled_entry(
            tab_pg,
            6,
            "Путь к pg_dumpall.exe:",
            self._pg_dumpall_path_var,
            button_text="Выбрать...",
            button_command=lambda: self._choose_file(
                self._pg_dumpall_path_var,
                "Выберите pg_dumpall.exe",
                [("Executable files", "*.exe"), ("All files", "*.*")],
            ),
        )

        self._add_labeled_entry(
            tab_backup,
            0,
            "Папка backup:",
            self._backup_dir_var,
            button_text="Выбрать...",
            button_command=lambda: self._choose_folder(self._backup_dir_var, "Выберите папку для backup"),
        )
        self._add_labeled_entry(tab_backup, 1, "Хранить дней:", self._retention_days_var)
        self._add_labeled_entry(tab_backup, 2, "Шаблон имени:", self._naming_pattern_var)
        self._add_labeled_entry(tab_backup, 3, "Имя общего лога:", self._main_log_name_var)
        self._add_labeled_entry(tab_backup, 4, "Log level:", self._log_level_var)
        ttk.Checkbutton(
            tab_backup,
            text="Выгружать globals (roles/tablespaces)",
            variable=self._dump_globals_var,
        ).grid(row=5, column=1, sticky="w", pady=4)

        ttk.Checkbutton(
            tab_scheduler,
            text="Включить планировщик для профиля",
            variable=self._scheduler_enabled_var,
        ).grid(row=0, column=1, sticky="w", pady=4)
        self._add_labeled_entry(tab_scheduler, 1, "Имя задачи:", self._task_name_var)
        self._add_labeled_combobox(
            tab_scheduler,
            2,
            "Тип расписания:",
            self._schedule_type_var,
            [item.value for item in ScheduleType],
        )
        self._add_labeled_entry(tab_scheduler, 3, "Время запуска (HH:MM):", self._start_time_var)
        self._add_labeled_entry(tab_scheduler, 4, "Дни недели (через запятую):", self._days_of_week_var)
        self._add_labeled_entry(tab_scheduler, 5, "Пользователь запуска:", self._run_user_var)
        self._add_labeled_entry(
            tab_scheduler,
            6,
            "Пароль запуска (не сохраняется):",
            self._run_password_var,
            show="*",
        )
        ttk.Checkbutton(
            tab_scheduler,
            text="Запускать с наивысшими правами",
            variable=self._run_with_highest_privileges_var,
        ).grid(row=7, column=1, sticky="w", pady=4)

        scheduler_actions = ttk.LabelFrame(tab_scheduler, text="Управление задачей", padding=10)
        scheduler_actions.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        scheduler_actions.columnconfigure(0, weight=1)

        ttk.Button(
            scheduler_actions,
            text="Создать / обновить задачу",
            command=self._create_or_update_scheduler_task,
        ).grid(row=0, column=0, sticky="w", padx=4, pady=4)

        ttk.Button(
            scheduler_actions,
            text="Проверить задачу",
            command=self._query_scheduler_task,
        ).grid(row=1, column=0, sticky="w", padx=4, pady=4)

        ttk.Button(
            scheduler_actions,
            text="Запустить задачу сейчас",
            command=self._run_scheduler_task_now,
        ).grid(row=2, column=0, sticky="w", padx=4, pady=4)

        ttk.Button(
            scheduler_actions,
            text="Удалить задачу",
            command=self._delete_scheduler_task,
        ).grid(row=3, column=0, sticky="w", padx=4, pady=4)

        ttk.Label(
            scheduler_actions,
            textvariable=self._scheduler_status_var,
            justify="left",
            wraplength=760,
            foreground="#333333",
        ).grid(row=4, column=0, sticky="w", padx=4, pady=(10, 4))

        actions = ttk.LabelFrame(tab_actions, text="Действия", padding=10)
        actions.grid(row=0, column=0, columnspan=2, sticky="ew")
        actions.columnconfigure(0, weight=1)

        ttk.Button(actions, text="Проверить профиль", command=self._validate_profile).grid(
            row=0, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Button(actions, text="Тестовый backup сейчас", command=self._run_test_backup).grid(
            row=1, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Button(actions, text="Открыть папку backup", command=self._open_backup_folder).grid(
            row=2, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Button(actions, text="Открыть папку приложения", command=self._open_app_folder).grid(
            row=3, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Button(actions, text="Закрыть", command=self._on_close).grid(
            row=4, column=0, sticky="w", padx=4, pady=(12, 4)
        )

        status_bar = ttk.Label(root, textvariable=self._status_var, anchor="w")
        status_bar.grid(row=2, column=0, sticky="ew", pady=(8, 0))

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

        self._attach_entry_behaviors(entry)
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
                row=row, column=2, padx=4, pady=4
            )

        return entry

    def _get_entry_widget(self, widget: object) -> EntryWidget | None:
        if isinstance(widget, (tk.Entry, ttk.Entry)):
            return cast(EntryWidget, widget)
        return None

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

    def _attach_entry_behaviors(self, entry: ttk.Entry) -> None:
        entry.bind("<Button-3>", self._show_entry_menu)
        entry.bind("<Control-a>", self._select_all)
        entry.bind("<Control-A>", self._select_all)
        entry.bind("<Control-Insert>", lambda e: self._generate_on_widget(e.widget, "<<Copy>>"))
        entry.bind("<Shift-Insert>", lambda e: self._generate_on_widget(e.widget, "<<Paste>>"))
        entry.bind("<Shift-Delete>", lambda e: self._generate_on_widget(e.widget, "<<Cut>>"))

    def _create_context_menu(self) -> None:
        self._entry_menu = tk.Menu(self, tearoff=0)
        self._entry_menu.add_command(label="Вырезать", command=lambda: self._clipboard_on_focus("<<Cut>>"))
        self._entry_menu.add_command(label="Копировать", command=lambda: self._clipboard_on_focus("<<Copy>>"))
        self._entry_menu.add_command(label="Вставить", command=lambda: self._clipboard_on_focus("<<Paste>>"))
        self._entry_menu.add_separator()
        self._entry_menu.add_command(label="Выделить всё", command=self._select_all_on_focus)

    def _show_entry_menu(self, event: tk.Event) -> str:
        if self._entry_menu is None:
            return "break"

        widget = event.widget
        widget.focus_set()

        try:
            self._entry_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._entry_menu.grab_release()

        return "break"

    def _clipboard_on_focus(self, virtual_event_name: str) -> None:
        entry = self._get_entry_widget(self.focus_get())
        if entry is None:
            return
        entry.event_generate(virtual_event_name)

    def _generate_on_widget(self, widget: tk.Widget, virtual_event_name: str) -> str:
        widget.event_generate(virtual_event_name)
        return "break"

    def _select_all(self, event: tk.Event) -> str | None:
        entry = self._get_entry_widget(event.widget)
        if entry is None:
            return None

        entry.selection_range(0, "end")
        entry.icursor("end")
        entry.xview("moveto", 0)
        return "break"

    def _select_all_on_focus(self) -> None:
        entry = self._get_entry_widget(self.focus_get())
        if entry is None:
            return

        entry.selection_range(0, "end")
        entry.icursor("end")
        entry.xview("moveto", 0)

    def _split_csv(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    def _current_profile_from_form(self) -> BackupProfile:
        try:
            port = int(self._port_var.get().strip() or "5432")
        except ValueError as exc:
            raise ValidationError("Port должен быть числом.") from exc

        try:
            retention_days = int(self._retention_days_var.get().strip() or "30")
        except ValueError as exc:
            raise ValidationError("Хранить дней должно быть числом.") from exc

        schedule_value = self._schedule_type_var.get().strip() or ScheduleType.DISABLED.value
        try:
            schedule_type = ScheduleType(schedule_value)
        except ValueError:
            schedule_type = ScheduleType.DISABLED

        return BackupProfile(
            schema_version=1,
            profile_name=self._profile_name_var.get().strip() or "New Profile",
            postgres=PostgresSettings(
                host=self._host_var.get().strip(),
                port=port,
                databases=self._split_csv(self._databases_var.get()),
                user=self._user_var.get().strip(),
                password=self._password_var.get(),
                pg_dump_path=self._pg_dump_path_var.get().strip(),
                pg_dumpall_path=self._pg_dumpall_path_var.get().strip(),
            ),
            backup=BackupSettings(
                backup_dir=self._backup_dir_var.get().strip(),
                retention_days=retention_days,
                dump_globals=bool(self._dump_globals_var.get()),
                naming_pattern=self._naming_pattern_var.get().strip() or "{database}_{timestamp}",
            ),
            logging=LoggingSettings(
                main_log_name=self._main_log_name_var.get().strip() or "backup.log",
                log_level=self._log_level_var.get().strip() or "INFO",
            ),
            scheduler=SchedulerSettings(
                enabled=bool(self._scheduler_enabled_var.get()),
                task_name=self._task_name_var.get().strip(),
                schedule_type=schedule_type,
                start_time=self._start_time_var.get().strip() or "02:00",
                days_of_week=self._split_csv(self._days_of_week_var.get()),
                run_user=self._run_user_var.get().strip(),
                run_with_highest_privileges=bool(self._run_with_highest_privileges_var.get()),
            ),
        )

    def _populate_form(self, profile: BackupProfile) -> None:
        self._profile_name_var.set(profile.profile_name)

        self._host_var.set(profile.postgres.host)
        self._port_var.set(str(profile.postgres.port))
        self._databases_var.set(", ".join(profile.postgres.databases))
        self._user_var.set(profile.postgres.user)
        self._password_var.set(profile.postgres.password)
        self._pg_dump_path_var.set(profile.postgres.pg_dump_path)
        self._pg_dumpall_path_var.set(profile.postgres.pg_dumpall_path)

        self._backup_dir_var.set(profile.backup.backup_dir)
        self._retention_days_var.set(str(profile.backup.retention_days))
        self._dump_globals_var.set(profile.backup.dump_globals)
        self._naming_pattern_var.set(profile.backup.naming_pattern)

        self._main_log_name_var.set(profile.logging.main_log_name)
        self._log_level_var.set(profile.logging.log_level)

        self._scheduler_enabled_var.set(profile.scheduler.enabled)
        self._task_name_var.set(profile.scheduler.task_name)
        self._schedule_type_var.set(profile.scheduler.schedule_type.value)
        self._start_time_var.set(profile.scheduler.start_time)
        self._days_of_week_var.set(", ".join(profile.scheduler.days_of_week))
        self._run_user_var.set(profile.scheduler.run_user)
        self._run_with_highest_privileges_var.set(profile.scheduler.run_with_highest_privileges)

    def _load_startup(self) -> None:
        try:
            self._app_settings = self._app_settings_service.load_settings(str(self._app_settings_path))
        except Exception:
            self._app_settings = AppSettings()

        width = max(self._app_settings.window_width, 920)
        height = max(self._app_settings.window_height, 680)
        self.geometry(f"{width}x{height}")

        last_profile_path = self._app_settings.last_profile_path.strip()
        if last_profile_path and Path(last_profile_path).exists():
            try:
                self._load_profile(last_profile_path)
                self._status("Загружен последний профиль.")
                return
            except Exception as exc:
                self._status(f"Не удалось загрузить последний профиль: {exc}")

        self._new_profile()

    def _new_profile(self) -> None:
        profile = self._profile_service.create_default_profile()
        self._populate_form(profile)
        self._profile_path_var.set("")
        self._scheduler_status_var.set("Статус задачи не запрошен.")
        self._status("Создан новый профиль.")

    def _browse_profile(self) -> None:
        current_path = self._profile_path_var.get().strip()
        initialdir = str(self._app_dir)
        initialfile = ""

        if current_path:
            path_obj = Path(current_path)
            if path_obj.is_file():
                initialdir = str(path_obj.parent)
                initialfile = path_obj.name
            elif path_obj.parent.exists():
                initialdir = str(path_obj.parent)
                initialfile = path_obj.name

        path = filedialog.askopenfilename(
            title="Выберите профиль backup",
            initialdir=initialdir,
            initialfile=initialfile,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._profile_path_var.set(path)

    def _load_profile_from_current_path(self) -> None:
        profile_path = self._profile_path_var.get().strip()
        if not profile_path:
            messagebox.showwarning("Нет пути", "Укажи путь к JSON-файлу профиля.")
            return
        self._load_profile(profile_path)

    def _load_profile(self, profile_path: str) -> None:
        profile = self._profile_service.load_profile(profile_path)
        self._populate_form(profile)
        self._profile_path_var.set(profile_path)
        self._app_settings = self._app_settings_service.register_recent_profile(self._app_settings, profile_path)
        self._scheduler_status_var.set("Статус задачи не запрошен.")
        self._status(f"Профиль загружен: {profile_path}")

    def _save_profile(self) -> None:
        profile_path = self._profile_path_var.get().strip()
        if not profile_path:
            self._save_profile_as()
            return

        profile = self._current_profile_from_form()
        self._profile_service.save_profile(profile_path, profile)
        self._app_settings = self._app_settings_service.register_recent_profile(self._app_settings, profile_path)
        self._status(f"Профиль сохранён: {profile_path}")
        messagebox.showinfo("Сохранено", f"Профиль сохранён:\n{profile_path}")

    def _save_profile_as(self) -> None:
        profile = self._current_profile_from_form()

        current_path = self._profile_path_var.get().strip()
        initialdir = str(self._app_dir)
        initialfile = self._profile_service.get_profile_file_name(profile)

        if current_path:
            path_obj = Path(current_path)
            if path_obj.parent.exists():
                initialdir = str(path_obj.parent)
            if path_obj.name:
                initialfile = path_obj.name

        path = filedialog.asksaveasfilename(
            title="Сохранить профиль backup как",
            defaultextension=".json",
            initialdir=initialdir,
            initialfile=initialfile,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        self._profile_service.save_profile(path, profile)
        self._profile_path_var.set(path)
        self._app_settings = self._app_settings_service.register_recent_profile(self._app_settings, path)
        self._status(f"Профиль сохранён: {path}")
        messagebox.showinfo("Сохранено", f"Профиль сохранён:\n{path}")

    def _ensure_profile_saved(self) -> tuple[str, BackupProfile]:
        profile_path = self._profile_path_var.get().strip()
        profile = self._current_profile_from_form()

        if not profile_path:
            initialdir = str(self._app_dir)
            initialfile = self._profile_service.get_profile_file_name(profile)

            profile_path = filedialog.asksaveasfilename(
                title="Сохранить профиль backup как",
                defaultextension=".json",
                initialdir=initialdir,
                initialfile=initialfile,
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
            if not profile_path:
                raise ValidationError("Операция отменена: профиль должен быть сохранён.")

            self._profile_path_var.set(profile_path)

        self._profile_service.save_profile(profile_path, profile)
        self._app_settings = self._app_settings_service.register_recent_profile(self._app_settings, profile_path)
        return profile_path, profile

    def _validate_profile(self) -> None:
        profile = self._current_profile_from_form()
        self._profile_service.validate_profile(profile)
        self._status("Профиль корректен.")
        messagebox.showinfo("Проверка", "Профиль корректен.")

    def _run_test_backup(self) -> None:
        profile = self._current_profile_from_form()
        result = self._backup_runner.run_profile(profile)
        self._show_backup_result(result)
        self._status("Тестовый backup выполнен успешно.")

    def _show_backup_result(self, result: BackupRunResult) -> None:
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

    def _create_or_update_scheduler_task(self) -> None:
        profile_path, profile = self._ensure_profile_saved()
        run_password = self._run_password_var.get().strip() or None

        output = self._scheduler_service.create_or_update_task(
            profile=profile,
            profile_path=profile_path,
            run_password=run_password,
        )
        self._run_password_var.set("")

        self._status("Задача Планировщика создана/обновлена.")
        info = self._scheduler_service.query_task(profile)
        self._update_scheduler_status(info)

        messagebox.showinfo(
            "Планировщик",
            f"Задача успешно создана/обновлена.\n\n{output or 'Команда выполнена успешно.'}",
        )

    def _query_scheduler_task(self) -> None:
        profile = self._current_profile_from_form()
        info = self._scheduler_service.query_task(profile)
        self._update_scheduler_status(info)
        self._status("Статус задачи обновлён.")

    def _run_scheduler_task_now(self) -> None:
        profile = self._current_profile_from_form()
        output = self._scheduler_service.run_task(profile)
        self._status("Задача Планировщика запущена.")
        self._scheduler_status_var.set(
            f"{self._scheduler_status_var.get()}\n\nПоследний запуск инициирован вручную."
        )
        messagebox.showinfo("Планировщик", output or "Задача успешно запущена.")

    def _delete_scheduler_task(self) -> None:
        profile = self._current_profile_from_form()

        if not messagebox.askyesno(
            "Удаление задачи",
            "Удалить задачу Планировщика для текущего профиля?",
        ):
            return

        output = self._scheduler_service.delete_task(profile)
        self._scheduler_status_var.set("Задача Планировщика удалена или не существовала.")
        self._status("Задача Планировщика удалена.")
        messagebox.showinfo("Планировщик", output or "Задача удалена.")

    def _update_scheduler_status(self, info: ScheduledTaskInfo) -> None:
        if not info.exists:
            self._scheduler_status_var.set(f"Задача '{info.task_name}' не найдена.")
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

        self._scheduler_status_var.set("\n".join(lines))

    def _choose_file(self, variable: tk.StringVar, title: str, filetypes: list[tuple[str, str]]) -> None:
        current_value = variable.get().strip()

        initialdir = str(self._app_dir)
        initialfile = ""

        if current_value:
            path_obj = Path(current_value)
            if path_obj.is_file():
                initialdir = str(path_obj.parent)
                initialfile = path_obj.name
            elif path_obj.parent.exists():
                initialdir = str(path_obj.parent)
                initialfile = path_obj.name

        path = filedialog.askopenfilename(
            title=title,
            initialdir=initialdir,
            initialfile=initialfile,
            filetypes=filetypes,
        )
        if path:
            variable.set(path)

    def _choose_folder(self, variable: tk.StringVar, title: str) -> None:
        current_value = variable.get().strip()
        initialdir = str(self._app_dir)

        if current_value:
            path_obj = Path(current_value)
            if path_obj.is_dir():
                initialdir = str(path_obj)
            elif path_obj.parent.exists():
                initialdir = str(path_obj.parent)

        path = filedialog.askdirectory(title=title, initialdir=initialdir)
        if path:
            variable.set(path)

    def _open_profile_folder(self) -> None:
        profile_path = self._profile_path_var.get().strip()
        if not profile_path:
            messagebox.showwarning("Нет пути", "Не указан путь к профилю.")
            return
        open_in_explorer(str(Path(profile_path).parent))

    def _open_backup_folder(self) -> None:
        backup_dir = self._backup_dir_var.get().strip()
        if not backup_dir:
            messagebox.showwarning("Нет пути", "Не указана папка backup.")
            return
        open_in_explorer(backup_dir)

    def _open_app_folder(self) -> None:
        open_in_explorer(str(self._app_dir))

    def _status(self, message: str) -> None:
        self._status_var.set(message)

    def _save_app_settings(self) -> None:
        self._app_settings.window_width = self.winfo_width()
        self._app_settings.window_height = self.winfo_height()
        self._app_settings.last_profile_path = self._profile_path_var.get().strip()
        self._app_settings_service.save_settings(str(self._app_settings_path), self._app_settings)

    def _on_close(self) -> None:
        try:
            self._save_app_settings()
        except Exception:
            pass
        self.destroy()


def run_main_window() -> int:
    try:
        app = MainWindow()
        app.mainloop()
        return 0
    except ValidationError as exc:
        messagebox.showerror("Validation error", str(exc))
        return 2
    except ConfigError as exc:
        messagebox.showerror("Config error", str(exc))
        return 3
    except BackupExecutionError as exc:
        messagebox.showerror("Backup execution error", str(exc))
        return 4
    except SchedulerError as exc:
        messagebox.showerror("Scheduler error", str(exc))
        return 5
    except Exception as exc:
        messagebox.showerror("Unexpected error", str(exc))
        return 99