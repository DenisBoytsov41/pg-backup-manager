from __future__ import annotations

from typing import Callable

from tkinter import ttk

from pg_backup_manager.ui.ui_style import LARGE_BUTTON_WIDTH, PAD_X, PAD_Y, SECTION_PAD_Y, TAB_PADDING


def build_actions_tab(
    *,
    parent: ttk.Frame,
    validate_profile: Callable[[], None],
    run_test_backup: Callable[[], None],
    open_backup_folder: Callable[[], None],
    open_app_folder: Callable[[], None],
    close_window: Callable[[], None],
) -> None:
    content = ttk.Frame(parent, padding=TAB_PADDING)
    content.grid(row=0, column=0, sticky="nsew")
    content.columnconfigure(0, weight=1)

    main_actions = ttk.LabelFrame(content, text="Основные действия", padding=12)
    main_actions.grid(row=0, column=0, sticky="ew")
    main_actions.columnconfigure(0, weight=1)
    main_actions.columnconfigure(1, weight=1)

    ttk.Button(
        main_actions,
        text="Проверить профиль",
        width=LARGE_BUTTON_WIDTH,
        command=validate_profile,
    ).grid(row=0, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)

    ttk.Button(
        main_actions,
        text="Тестовый backup",
        width=LARGE_BUTTON_WIDTH,
        command=run_test_backup,
    ).grid(row=0, column=1, sticky="w", padx=PAD_X, pady=PAD_Y)

    extra_actions = ttk.LabelFrame(content, text="Дополнительно", padding=12)
    extra_actions.grid(row=1, column=0, sticky="ew", pady=(SECTION_PAD_Y, 0))
    extra_actions.columnconfigure(0, weight=1)
    extra_actions.columnconfigure(1, weight=1)

    ttk.Button(
        extra_actions,
        text="Открыть папку backup",
        width=LARGE_BUTTON_WIDTH,
        command=open_backup_folder,
    ).grid(row=0, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)

    ttk.Button(
        extra_actions,
        text="Открыть папку приложения",
        width=LARGE_BUTTON_WIDTH,
        command=open_app_folder,
    ).grid(row=0, column=1, sticky="w", padx=PAD_X, pady=PAD_Y)

    bottom_actions = ttk.Frame(content)
    bottom_actions.grid(row=2, column=0, sticky="w", pady=(SECTION_PAD_Y, 0))

    ttk.Button(
        bottom_actions,
        text="Закрыть",
        width=LARGE_BUTTON_WIDTH,
        command=close_window,
    ).grid(row=0, column=0, sticky="w")