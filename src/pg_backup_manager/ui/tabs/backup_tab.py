from __future__ import annotations

import tkinter as tk
from typing import Callable

from tkinter import ttk

from pg_backup_manager.ui.form_state import MainWindowState


def build_backup_tab(
    *,
    parent: ttk.Frame,
    state: MainWindowState,
    add_labeled_entry: Callable[..., ttk.Entry],
    choose_folder: Callable[[tk.StringVar, str], None],
) -> None:
    add_labeled_entry(
        parent,
        0,
        "Папка backup:",
        state.backup_dir_var,
        button_text="Выбрать...",
        button_command=lambda: choose_folder(
            state.backup_dir_var,
            "Выберите папку для backup",
        ),
    )
    add_labeled_entry(parent, 1, "Хранить дней:", state.retention_days_var)
    add_labeled_entry(parent, 2, "Шаблон имени:", state.naming_pattern_var)
    add_labeled_entry(parent, 3, "Имя общего лога:", state.main_log_name_var)
    add_labeled_entry(parent, 4, "Log level:", state.log_level_var)

    ttk.Checkbutton(
        parent,
        text="Выгружать globals (roles/tablespaces)",
        variable=state.dump_globals_var,
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