from __future__ import annotations

import tkinter as tk
from typing import Callable

from tkinter import ttk

from pg_backup_manager.ui.form_state import MainWindowState
from pg_backup_manager.ui.ui_style import (
    PAD_X,
    PAD_Y,
    SECTION_PAD_Y,
    TAB_PADDING,
    WRAP_WIDTH_DEFAULT,
)


def build_backup_tab(
    *,
    parent: ttk.Frame,
    state: MainWindowState,
    add_labeled_entry: Callable[..., ttk.Entry],
    choose_folder: Callable[[tk.StringVar, str], None],
) -> None:
    content = ttk.Frame(parent, padding=TAB_PADDING)
    content.grid(row=0, column=0, sticky="nsew")
    content.columnconfigure(0, weight=1)

    files_frame = ttk.LabelFrame(content, text="Файлы backup", padding=12)
    files_frame.grid(row=0, column=0, sticky="ew")
    files_frame.columnconfigure(1, weight=1)

    add_labeled_entry(
        files_frame,
        0,
        "Папка backup:",
        state.backup_dir_var,
        button_text="Выбрать...",
        button_command=lambda: choose_folder(
            state.backup_dir_var,
            "Выберите папку для backup",
        ),
    )
    add_labeled_entry(files_frame, 1, "Хранить дней:", state.retention_days_var)
    add_labeled_entry(files_frame, 2, "Шаблон имени:", state.naming_pattern_var)

    ttk.Checkbutton(
        files_frame,
        text="Выгружать globals (roles/tablespaces)",
        variable=state.dump_globals_var,
    ).grid(row=3, column=1, sticky="w", pady=PAD_Y)

    ttk.Label(
        files_frame,
        text=(
            "Шаблон имени может использовать: {database}, {timestamp}, {profile}. "
            "Обязательны {database} и {timestamp}."
        ),
        foreground="#555555",
        wraplength=WRAP_WIDTH_DEFAULT,
        justify="left",
    ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(PAD_Y, 0))

    ttk.Label(
        files_frame,
        text="При значении 0 автоочистка старых .backup/.log/.sql файлов отключается.",
        foreground="#555555",
        wraplength=WRAP_WIDTH_DEFAULT,
        justify="left",
    ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(PAD_Y, 0))

    logging_frame = ttk.LabelFrame(content, text="Логирование", padding=12)
    logging_frame.grid(row=1, column=0, sticky="ew", pady=(SECTION_PAD_Y, 0))
    logging_frame.columnconfigure(1, weight=1)

    add_labeled_entry(logging_frame, 0, "Имя общего лога:", state.main_log_name_var)
    add_labeled_entry(logging_frame, 1, "Log level:", state.log_level_var)

    ttk.Label(
        logging_frame,
        text=(
            "Общий лог хранит основные события приложения. "
            "Для каждого запуска backup также создаётся отдельный run-log."
        ),
        foreground="#555555",
        wraplength=WRAP_WIDTH_DEFAULT,
        justify="left",
    ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(PAD_Y, 0))

    hints_frame = ttk.LabelFrame(content, text="Подсказки", padding=12)
    hints_frame.grid(row=2, column=0, sticky="ew", pady=(SECTION_PAD_Y, 0))
    hints_frame.columnconfigure(0, weight=1)

    ttk.Label(
        hints_frame,
        text=(
            "Если включена выгрузка globals, должен быть указан путь к pg_dumpall.exe.\n"
            "Для регулярной работы рекомендуется использовать отдельную папку backup."
        ),
        foreground="#555555",
        wraplength=WRAP_WIDTH_DEFAULT,
        justify="left",
    ).grid(row=0, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)