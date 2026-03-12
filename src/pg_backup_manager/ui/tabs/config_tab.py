from __future__ import annotations

from typing import Callable

from tkinter import ttk

from pg_backup_manager.ui.form_state import MainWindowState
from pg_backup_manager.ui.ui_style import (
    PAD_X,
    PAD_Y,
    SECTION_PAD_Y,
    TAB_PADDING,
    WRAP_WIDTH_WIDE,
)


def build_config_tab(
    *,
    parent: ttk.Frame,
    state: MainWindowState,
    add_labeled_entry: Callable[..., ttk.Entry],
) -> None:
    content = ttk.Frame(parent, padding=TAB_PADDING)
    content.grid(row=0, column=0, sticky="nsew")
    content.columnconfigure(0, weight=1)

    profile_frame = ttk.LabelFrame(content, text="Основная информация", padding=12)
    profile_frame.grid(row=0, column=0, sticky="ew")
    profile_frame.columnconfigure(1, weight=1)

    add_labeled_entry(profile_frame, 0, "Имя профиля:", state.profile_name_var)

    ttk.Label(
        profile_frame,
        text=(
            "Имя профиля используется для отображения в интерфейсе и может "
            "участвовать в шаблоне имени backup-файлов."
        ),
        foreground="#555555",
        wraplength=WRAP_WIDTH_WIDE,
        justify="left",
    ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(PAD_Y, 0))

    purpose_frame = ttk.LabelFrame(content, text="Назначение профиля", padding=12)
    purpose_frame.grid(row=1, column=0, sticky="ew", pady=(SECTION_PAD_Y, 0))
    purpose_frame.columnconfigure(0, weight=1)

    ttk.Label(
        purpose_frame,
        text=(
            "Профиль хранит полный набор параметров для backup: подключение к PostgreSQL, "
            "папку хранения, правила именования файлов, параметры логирования и настройки "
            "Планировщика задач Windows."
        ),
        foreground="#333333",
        wraplength=WRAP_WIDTH_WIDE,
        justify="left",
    ).grid(row=0, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)

    hints_frame = ttk.LabelFrame(content, text="Рекомендации", padding=12)
    hints_frame.grid(row=2, column=0, sticky="ew", pady=(SECTION_PAD_Y, 0))
    hints_frame.columnconfigure(0, weight=1)

    ttk.Label(
        hints_frame,
        text=(
            "• Используй понятное имя профиля, чтобы его было легко отличать в списке файлов.\n"
            "• Если у тебя несколько сценариев backup, лучше заводить отдельный профиль под каждый.\n"
            "• Перед включением расписания сначала проверь профиль вручную через вкладку «Действия»."
        ),
        foreground="#555555",
        wraplength=WRAP_WIDTH_WIDE,
        justify="left",
    ).grid(row=0, column=0, sticky="w", padx=PAD_X, pady=PAD_Y)