from __future__ import annotations

import tkinter as tk
from typing import Callable

from tkinter import ttk

from pg_backup_manager.domain.models import ScheduleType
from pg_backup_manager.ui.form_state import MainWindowState
from pg_backup_manager.ui.ui_style import (
    LARGE_BUTTON_WIDTH,
    PAD_X,
    PAD_Y,
    SECTION_PAD_Y,
    TAB_PADDING,
    WRAP_WIDTH_DEFAULT,
    WRAP_WIDTH_STATUS,
)


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
    content = ttk.Frame(parent, padding=TAB_PADDING)
    content.grid(row=0, column=0, sticky="nsew")
    content.columnconfigure(0, weight=1)

    schedule_frame = ttk.LabelFrame(content, text="Параметры задачи", padding=12)
    schedule_frame.grid(row=0, column=0, sticky="ew")
    schedule_frame.columnconfigure(1, weight=1)

    ttk.Checkbutton(
        schedule_frame,
        text="Включить планировщик для профиля",
        variable=state.scheduler_enabled_var,
    ).grid(row=0, column=1, sticky="w", pady=PAD_Y)

    add_labeled_entry(schedule_frame, 1, "Имя задачи:", state.task_name_var)

    add_labeled_combobox(
        schedule_frame,
        2,
        "Тип расписания:",
        state.schedule_type_var,
        [item.value for item in ScheduleType],
    )

    add_labeled_entry(schedule_frame, 3, "Время запуска (HH:MM):", state.start_time_var)

    days_of_week_entry = add_labeled_entry(
        schedule_frame,
        4,
        "Дни недели (через запятую):",
        state.days_of_week_var,
    )

    ttk.Label(
        schedule_frame,
        text=(
            "Если планировщик включён, имя задачи обязательно, "
            "а тип расписания не должен быть disabled."
        ),
        foreground="#555555",
        wraplength=WRAP_WIDTH_DEFAULT,
        justify="left",
    ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(PAD_Y, 0))

    run_frame = ttk.LabelFrame(content, text="Параметры запуска", padding=12)
    run_frame.grid(row=1, column=0, sticky="ew", pady=(SECTION_PAD_Y, 0))
    run_frame.columnconfigure(1, weight=1)

    add_labeled_entry(run_frame, 0, "Пользователь запуска:", state.run_user_var)
    add_labeled_entry(
        run_frame,
        1,
        "Пароль запуска (не сохраняется):",
        state.run_password_var,
        show="*",
    )

    ttk.Checkbutton(
        run_frame,
        text="Запускать с наивысшими правами",
        variable=state.run_with_highest_privileges_var,
    ).grid(row=2, column=1, sticky="w", pady=PAD_Y)

    actions_frame = ttk.LabelFrame(content, text="Управление задачей", padding=12)
    actions_frame.grid(row=2, column=0, sticky="ew", pady=(SECTION_PAD_Y, 0))
    actions_frame.columnconfigure(0, weight=1)

    create_button = ttk.Button(
        actions_frame,
        text="Создать / обновить задачу",
        width=LARGE_BUTTON_WIDTH,
        command=create_or_update_task,
    )
    create_button.grid(row=0, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)

    ttk.Button(
        actions_frame,
        text="Проверить задачу",
        width=LARGE_BUTTON_WIDTH,
        command=query_task,
    ).grid(row=1, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)

    ttk.Button(
        actions_frame,
        text="Запустить задачу",
        width=LARGE_BUTTON_WIDTH,
        command=run_task_now,
    ).grid(row=2, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)

    ttk.Button(
        actions_frame,
        text="Удалить задачу",
        width=LARGE_BUTTON_WIDTH,
        command=delete_task,
    ).grid(row=3, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)

    ttk.Label(
        actions_frame,
        textvariable=state.scheduler_status_var,
        justify="left",
        wraplength=WRAP_WIDTH_STATUS,
        foreground="#333333",
    ).grid(row=4, column=0, sticky="w", padx=PAD_X, pady=(SECTION_PAD_Y, PAD_Y))

    return days_of_week_entry, create_button