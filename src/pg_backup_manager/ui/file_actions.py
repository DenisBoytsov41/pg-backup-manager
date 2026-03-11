from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Sequence

from tkinter import filedialog, messagebox


FileType = tuple[str, str]


def build_dialog_initial_state(
    current_value: str,
    fallback_dir: str | Path,
) -> tuple[str, str]:
    initialdir = str(Path(fallback_dir))
    initialfile = ""

    normalized_value = current_value.strip()
    if not normalized_value:
        return initialdir, initialfile

    path_obj = Path(normalized_value).expanduser()

    if path_obj.is_file():
        return str(path_obj.parent), path_obj.name

    if path_obj.is_dir():
        return str(path_obj), ""

    if path_obj.parent.exists():
        return str(path_obj.parent), path_obj.name

    return initialdir, initialfile


def ask_open_file(
    *,
    title: str,
    current_value: str = "",
    fallback_dir: str | Path,
    filetypes: Sequence[FileType],
) -> str:
    initialdir, initialfile = build_dialog_initial_state(current_value, fallback_dir)

    return filedialog.askopenfilename(
        title=title,
        initialdir=initialdir,
        initialfile=initialfile,
        filetypes=list(filetypes),
    )


def ask_save_file(
    *,
    title: str,
    current_value: str = "",
    fallback_dir: str | Path,
    initialfile: str = "",
    defaultextension: str = "",
    filetypes: Sequence[FileType],
) -> str:
    dialog_initialdir, dialog_initialfile = build_dialog_initial_state(current_value, fallback_dir)

    if initialfile and not dialog_initialfile:
        dialog_initialfile = initialfile

    return filedialog.asksaveasfilename(
        title=title,
        defaultextension=defaultextension,
        initialdir=dialog_initialdir,
        initialfile=dialog_initialfile,
        filetypes=list(filetypes),
    )


def ask_directory(
    *,
    title: str,
    current_value: str = "",
    fallback_dir: str | Path,
) -> str:
    initialdir = str(Path(fallback_dir))

    normalized_value = current_value.strip()
    if normalized_value:
        path_obj = Path(normalized_value).expanduser()

        if path_obj.is_dir():
            initialdir = str(path_obj)
        elif path_obj.parent.exists():
            initialdir = str(path_obj.parent)

    return filedialog.askdirectory(
        title=title,
        initialdir=initialdir,
    )


def open_in_explorer(path: str | Path) -> None:
    normalized = str(path).strip()
    if not normalized:
        return

    normalized = os.path.normpath(normalized)

    if not os.path.exists(normalized):
        messagebox.showwarning("Путь не найден", f"Путь не существует:\n{normalized}")
        return

    if os.name == "nt":
        os.startfile(normalized)
        return

    if os.name == "posix":
        subprocess.Popen(["xdg-open", normalized])
        return

    messagebox.showinfo("Путь", normalized)