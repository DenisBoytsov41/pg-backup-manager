from __future__ import annotations

import tkinter as tk
from typing import Callable

from tkinter import ttk

from pg_backup_manager.ui.form_state import MainWindowState


def build_postgres_tab(
    *,
    parent: ttk.Frame,
    state: MainWindowState,
    add_labeled_entry: Callable[..., ttk.Entry],
    choose_file: Callable[[tk.StringVar, str, list[tuple[str, str]]], None],
) -> None:
    add_labeled_entry(parent, 0, "Host:", state.host_var)
    add_labeled_entry(parent, 1, "Port:", state.port_var)
    add_labeled_entry(parent, 2, "Базы (через запятую):", state.databases_var)
    add_labeled_entry(parent, 3, "User:", state.user_var)
    add_labeled_entry(parent, 4, "Password:", state.password_var, show="*")

    add_labeled_entry(
        parent,
        5,
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
        parent,
        6,
        "Путь к pg_dumpall.exe:",
        state.pg_dumpall_path_var,
        button_text="Выбрать...",
        button_command=lambda: choose_file(
            state.pg_dumpall_path_var,
            "Выберите pg_dumpall.exe",
            [("Executable files", "*.exe"), ("All files", "*.*")],
        ),
    )