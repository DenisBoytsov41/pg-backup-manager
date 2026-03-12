from __future__ import annotations

from typing import Callable

from tkinter import ttk

from pg_backup_manager.ui.form_state import MainWindowState


def build_config_tab(
    *,
    parent: ttk.Frame,
    state: MainWindowState,
    add_labeled_entry: Callable[..., ttk.Entry],
) -> None:
    add_labeled_entry(parent, 0, "Имя профиля:", state.profile_name_var)

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