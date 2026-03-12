from __future__ import annotations

from typing import Callable

from tkinter import ttk


def build_actions_tab(
    *,
    parent: ttk.Frame,
    validate_profile: Callable[[], None],
    run_test_backup: Callable[[], None],
    open_backup_folder: Callable[[], None],
    open_app_folder: Callable[[], None],
    close_window: Callable[[], None],
) -> None:
    actions = ttk.LabelFrame(parent, text="Действия", padding=10)
    actions.grid(row=0, column=0, columnspan=2, sticky="ew")
    actions.columnconfigure(0, weight=1)

    ttk.Button(actions, text="Проверить профиль", command=validate_profile).grid(
        row=0, column=0, sticky="w", padx=4, pady=4
    )
    ttk.Button(actions, text="Тестовый backup сейчас", command=run_test_backup).grid(
        row=1, column=0, sticky="w", padx=4, pady=4
    )
    ttk.Button(actions, text="Открыть папку backup", command=open_backup_folder).grid(
        row=2, column=0, sticky="w", padx=4, pady=4
    )
    ttk.Button(actions, text="Открыть папку приложения", command=open_app_folder).grid(
        row=3, column=0, sticky="w", padx=4, pady=4
    )
    ttk.Button(actions, text="Закрыть", command=close_window).grid(
        row=4, column=0, sticky="w", padx=4, pady=(12, 4)
    )