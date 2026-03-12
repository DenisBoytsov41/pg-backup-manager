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


def build_postgres_tab(
    *,
    parent: ttk.Frame,
    state: MainWindowState,
    add_labeled_entry: Callable[..., ttk.Entry],
    choose_file: Callable[[tk.StringVar, str, list[tuple[str, str]]], None],
) -> None:
    content = ttk.Frame(parent, padding=TAB_PADDING)
    content.grid(row=0, column=0, sticky="nsew")
    content.columnconfigure(0, weight=1)

    connection_frame = ttk.LabelFrame(content, text="Подключение", padding=12)
    connection_frame.grid(row=0, column=0, sticky="ew")
    connection_frame.columnconfigure(1, weight=1)

    add_labeled_entry(connection_frame, 0, "Host:", state.host_var)
    add_labeled_entry(connection_frame, 1, "Port:", state.port_var)
    add_labeled_entry(connection_frame, 2, "Базы (через запятую):", state.databases_var)
    add_labeled_entry(connection_frame, 3, "User:", state.user_var)
    add_labeled_entry(connection_frame, 4, "Password:", state.password_var, show="*")

    ttk.Label(
        connection_frame,
        text=(
            "Укажи адрес сервера PostgreSQL, пользователя и список баз, "
            "которые нужно включить в backup."
        ),
        foreground="#555555",
        wraplength=WRAP_WIDTH_DEFAULT,
        justify="left",
    ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(PAD_Y, 0))

    tools_frame = ttk.LabelFrame(content, text="Утилиты PostgreSQL", padding=12)
    tools_frame.grid(row=1, column=0, sticky="ew", pady=(SECTION_PAD_Y, 0))
    tools_frame.columnconfigure(1, weight=1)

    add_labeled_entry(
        tools_frame,
        0,
        "Путь к pg_dump.exe:",
        state.pg_dump_path_var,
        button_text="Выбрать...",
        button_command=lambda: choose_file(
            state.pg_dump_path_var,
            "Выберите pg_dump.exe",
            [("Executable files", "*.exe"), ("All files", "*.*")],
        ),
    )

    add_labeled_entry(
        tools_frame,
        1,
        "Путь к pg_dumpall.exe:",
        state.pg_dumpall_path_var,
        button_text="Выбрать...",
        button_command=lambda: choose_file(
            state.pg_dumpall_path_var,
            "Выберите pg_dumpall.exe",
            [("Executable files", "*.exe"), ("All files", "*.*")],
        ),
    )

    ttk.Label(
        tools_frame,
        text=(
            "pg_dump.exe обязателен для backup баз. "
            "pg_dumpall.exe нужен для отдельной выгрузки globals."
        ),
        foreground="#555555",
        wraplength=WRAP_WIDTH_DEFAULT,
        justify="left",
    ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(PAD_Y, 0))