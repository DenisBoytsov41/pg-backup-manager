from __future__ import annotations

import tkinter as tk
from typing import Callable

from tkinter import ttk

from pg_backup_manager.domain.models import ScheduleType
from pg_backup_manager.ui.form_state import MainWindowState


def build_scheduler_tab(
    *,
    parent: ttk.Frame,
    state: MainWindowState,
    add_labeled_entry: Callable[..., ttk.Entry],
    add_labeled_combobox: Callable[[ttk.Widget, int, str, tk.StringVar, list[str]], ttk.Combobox],
    create_or_update_task: Callable[[], None],
    query_task: Callable[[], None],
    run_task_now: Callable[[], None],
    delete_task: Callable[[], None],
) -> tuple[ttk.Entry, ttk.Button]:
    ttk.Checkbutton(
        parent,
        text="Включить планировщик для профиля",
        variable=state.scheduler_enabled_var,
    ).grid(row=0, column=1, sticky="w", pady=4)

    add_labeled_entry(parent, 1, "Имя задачи:", state.task_name_var)

    add_labeled_combobox(
        parent,
        2,
        "Тип расписания:",
        state.schedule_type_var,
        [item.value for item in ScheduleType],
    )

    add_labeled_entry(parent, 3, "Время запуска (HH:MM):", state.start_time_var)

    days_of_week_entry = add_labeled_entry(
        parent,
        4,
        "Дни недели (через запятую):",
        state.days_of_week_var,
    )

    add_labeled_entry(parent, 5, "Пользователь запуска:", state.run_user_var)
    add_labeled_entry(
        parent,
        6,
        "Пароль запуска (не сохраняется):",
        state.run_password_var,
        show="*",
    )

    ttk.Checkbutton(
        parent,
        text="Запускать с наивысшими правами",
        variable=state.run_with_highest_privileges_var,
    ).grid(row=7, column=1, sticky="w", pady=4)

    ttk.Label(
        parent,
        text=(
            "Если планировщик включён, имя задачи обязательно, "
            "а тип расписания не должен быть disabled."
        ),
        foreground="#555555",
        wraplength=780,
        justify="left",
    ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(6, 8))

    scheduler_actions = ttk.LabelFrame(parent, text="Управление задачей", padding=10)
    scheduler_actions.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(12, 0))
    scheduler_actions.columnconfigure(0, weight=1)

    create_button = ttk.Button(
        scheduler_actions,
        text="Создать / обновить задачу",
        command=create_or_update_task,
    )
    create_button.grid(row=0, column=0, sticky="w", padx=4, pady=4)

    ttk.Button(
        scheduler_actions,
        text="Проверить задачу",
        command=query_task,
    ).grid(row=1, column=0, sticky="w", padx=4, pady=4)

    ttk.Button(
        scheduler_actions,
        text="Запустить задачу сейчас",
        command=run_task_now,
    ).grid(row=2, column=0, sticky="w", padx=4, pady=4)

    ttk.Button(
        scheduler_actions,
        text="Удалить задачу",
        command=delete_task,
    ).grid(row=3, column=0, sticky="w", padx=4, pady=4)

    ttk.Label(
        scheduler_actions,
        textvariable=state.scheduler_status_var,
        justify="left",
        wraplength=760,
        foreground="#333333",
    ).grid(row=4, column=0, sticky="w", padx=4, pady=(10, 4))

    return days_of_week_entry, create_button