from __future__ import annotations

from dataclasses import dataclass

import tkinter as tk

from pg_backup_manager.domain.models import ScheduleType


@dataclass(slots=True)
class MainWindowState:
    status_var: tk.StringVar
    scheduler_status_var: tk.StringVar
    dirty_var: tk.BooleanVar

    profile_path_var: tk.StringVar
    profile_name_var: tk.StringVar

    host_var: tk.StringVar
    port_var: tk.StringVar
    databases_var: tk.StringVar
    user_var: tk.StringVar
    password_var: tk.StringVar
    pg_dump_path_var: tk.StringVar
    pg_dumpall_path_var: tk.StringVar

    backup_dir_var: tk.StringVar
    retention_days_var: tk.StringVar
    dump_globals_var: tk.BooleanVar
    naming_pattern_var: tk.StringVar

    main_log_name_var: tk.StringVar
    log_level_var: tk.StringVar

    scheduler_enabled_var: tk.BooleanVar
    task_name_var: tk.StringVar
    schedule_type_var: tk.StringVar
    start_time_var: tk.StringVar
    days_of_week_var: tk.StringVar
    run_user_var: tk.StringVar
    run_password_var: tk.StringVar
    run_with_highest_privileges_var: tk.BooleanVar

    @classmethod
    def create(cls, master: tk.Misc) -> "MainWindowState":
        return cls(
            status_var=tk.StringVar(master=master, value="Готово."),
            scheduler_status_var=tk.StringVar(master=master, value="Статус задачи не запрошен."),
            dirty_var=tk.BooleanVar(master=master, value=False),

            profile_path_var=tk.StringVar(master=master),
            profile_name_var=tk.StringVar(master=master),

            host_var=tk.StringVar(master=master),
            port_var=tk.StringVar(master=master, value="5432"),
            databases_var=tk.StringVar(master=master),
            user_var=tk.StringVar(master=master, value="postgres"),
            password_var=tk.StringVar(master=master),
            pg_dump_path_var=tk.StringVar(master=master),
            pg_dumpall_path_var=tk.StringVar(master=master),

            backup_dir_var=tk.StringVar(master=master),
            retention_days_var=tk.StringVar(master=master, value="30"),
            dump_globals_var=tk.BooleanVar(master=master, value=True),
            naming_pattern_var=tk.StringVar(master=master, value="{database}_{timestamp}"),

            main_log_name_var=tk.StringVar(master=master, value="backup.log"),
            log_level_var=tk.StringVar(master=master, value="INFO"),

            scheduler_enabled_var=tk.BooleanVar(master=master, value=False),
            task_name_var=tk.StringVar(master=master),
            schedule_type_var=tk.StringVar(master=master, value=ScheduleType.DISABLED.value),
            start_time_var=tk.StringVar(master=master, value="02:00"),
            days_of_week_var=tk.StringVar(master=master),
            run_user_var=tk.StringVar(master=master),
            run_password_var=tk.StringVar(master=master),
            run_with_highest_privileges_var=tk.BooleanVar(master=master, value=False),
        )

    def mark_dirty(self, *_args: object) -> None:
        self.dirty_var.set(True)

    def mark_clean(self) -> None:
        self.dirty_var.set(False)

    def reset_runtime_fields(self) -> None:
        self.run_password_var.set("")

    def reset_scheduler_status(self) -> None:
        self.scheduler_status_var.set("Статус задачи не запрошен.")

    def set_status(self, message: str) -> None:
        self.status_var.set(message)