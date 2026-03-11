from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from typing import cast


EntryWidget = tk.Entry | ttk.Entry


@dataclass(slots=True)
class _EntryHistory:
    snapshots: list[str]
    index: int = 0


class EntryContextMenuManager:

    _KEY_A = 65
    _KEY_C = 67
    _KEY_V = 86
    _KEY_X = 88
    _KEY_Y = 89
    _KEY_Z = 90

    _CTRL_MASK = 0x0004
    _SHIFT_MASK = 0x0001

    def __init__(self, owner: tk.Misc) -> None:
        self._owner = owner
        self._menu = tk.Menu(owner, tearoff=0)

        self._histories: dict[EntryWidget, _EntryHistory] = {}
        self._suspended_widgets: set[EntryWidget] = set()

        self._menu.add_command(label="Отменить", command=self.undo_on_focus)
        self._menu.add_command(label="Повторить", command=self.redo_on_focus)
        self._menu.add_separator()
        self._menu.add_command(label="Вырезать", command=self.cut_on_focus)
        self._menu.add_command(label="Копировать", command=self.copy_on_focus)
        self._menu.add_command(label="Вставить", command=self.paste_on_focus)
        self._menu.add_separator()
        self._menu.add_command(label="Выделить всё", command=self.select_all_on_focus)

    def attach(self, entry: EntryWidget) -> None:
        self._reset_history(entry)

        entry.bind("<Button-3>", self.show_menu)
        entry.bind("<Shift-F10>", self._show_menu_from_keyboard)
        entry.bind("<KeyPress-Menu>", self._show_menu_from_keyboard)

        entry.bind("<KeyPress>", self._on_key_press, add="+")
        entry.bind("<KeyRelease>", self._on_key_release, add="+")

        entry.bind("<Control-Insert>", lambda e: self._copy_from_widget(e.widget), add="+")
        entry.bind("<Shift-Insert>", lambda e: self._paste_into_widget(e.widget), add="+")
        entry.bind("<Shift-Delete>", lambda e: self._cut_from_widget(e.widget), add="+")

        entry.bind("<FocusIn>", self._on_focus_in, add="+")

    def attach_many(self, *entries: EntryWidget) -> None:
        for entry in entries:
            self.attach(entry)

    def show_menu(self, event: tk.Event) -> str:
        entry = self._get_entry_widget(event.widget)
        if entry is None:
            return "break"

        entry.focus_set()
        self._update_menu_state(entry)

        try:
            self._menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu.grab_release()

        return "break"

    def copy_on_focus(self) -> None:
        entry = self._get_entry_widget(self._owner.focus_get())
        if entry is None:
            return
        self._copy_entry(entry)

    def cut_on_focus(self) -> None:
        entry = self._get_entry_widget(self._owner.focus_get())
        if entry is None:
            return
        self._cut_entry(entry)

    def paste_on_focus(self) -> None:
        entry = self._get_entry_widget(self._owner.focus_get())
        if entry is None:
            return
        self._paste_entry(entry)

    def undo_on_focus(self) -> None:
        entry = self._get_entry_widget(self._owner.focus_get())
        if entry is None:
            return
        self._undo_entry(entry)

    def redo_on_focus(self) -> None:
        entry = self._get_entry_widget(self._owner.focus_get())
        if entry is None:
            return
        self._redo_entry(entry)

    def select_all_on_focus(self) -> None:
        entry = self._get_entry_widget(self._owner.focus_get())
        if entry is None:
            return
        self._select_all_entry(entry)

    def _on_key_press(self, event: tk.Event) -> str | None:
        entry = self._get_entry_widget(event.widget)
        if entry is None:
            return None

        keycode = getattr(event, "keycode", None)
        state = getattr(event, "state", 0)

        ctrl_pressed = bool(state & self._CTRL_MASK)
        shift_pressed = bool(state & self._SHIFT_MASK)

        if ctrl_pressed:
            if keycode == self._KEY_A:
                self._select_all_entry(entry)
                return "break"

            if keycode == self._KEY_C:
                self._copy_entry(entry)
                return "break"

            if keycode == self._KEY_V:
                self._paste_entry(entry)
                return "break"

            if keycode == self._KEY_X:
                self._cut_entry(entry)
                return "break"

            if keycode == self._KEY_Z:
                if shift_pressed:
                    self._redo_entry(entry)
                else:
                    self._undo_entry(entry)
                return "break"

            if keycode == self._KEY_Y:
                self._redo_entry(entry)
                return "break"

        return None

    def _on_key_release(self, event: tk.Event) -> None:
        entry = self._get_entry_widget(event.widget)
        if entry is None:
            return

        keycode = getattr(event, "keycode", None)
        state = getattr(event, "state", 0)
        ctrl_pressed = bool(state & self._CTRL_MASK)

        if ctrl_pressed and keycode in {
            self._KEY_A,
            self._KEY_C,
            self._KEY_V,
            self._KEY_X,
            self._KEY_Y,
            self._KEY_Z,
        }:
            return

        self._schedule_record(entry)

    def _copy_from_widget(self, widget: tk.Widget) -> str:
        entry = self._get_entry_widget(widget)
        if entry is None:
            return "break"
        self._copy_entry(entry)
        return "break"

    def _paste_into_widget(self, widget: tk.Widget) -> str:
        entry = self._get_entry_widget(widget)
        if entry is None:
            return "break"
        self._paste_entry(entry)
        return "break"

    def _cut_from_widget(self, widget: tk.Widget) -> str:
        entry = self._get_entry_widget(widget)
        if entry is None:
            return "break"
        self._cut_entry(entry)
        return "break"


    def _copy_entry(self, entry: EntryWidget) -> None:
        entry.event_generate("<<Copy>>")

    def _cut_entry(self, entry: EntryWidget) -> None:
        self._ensure_history(entry)
        entry.event_generate("<<Cut>>")
        self._schedule_record(entry)

    def _paste_entry(self, entry: EntryWidget) -> None:
        self._ensure_history(entry)
        entry.event_generate("<<Paste>>")
        self._schedule_record(entry)


    def _undo_entry(self, entry: EntryWidget) -> None:
        history = self._ensure_history(entry)
        if history.index <= 0:
            return

        history.index -= 1
        self._replace_text(entry, history.snapshots[history.index])

    def _redo_entry(self, entry: EntryWidget) -> None:
        history = self._ensure_history(entry)
        if history.index >= len(history.snapshots) - 1:
            return

        history.index += 1
        self._replace_text(entry, history.snapshots[history.index])


    def _select_all_entry(self, entry: EntryWidget) -> None:
        entry.selection_range(0, "end")
        entry.icursor("end")
        entry.xview("moveto", 0)

    def _update_menu_state(self, entry: EntryWidget) -> None:
        has_selection = bool(entry.selection_present())
        history = self._ensure_history(entry)

        can_undo = history.index > 0
        can_redo = history.index < len(history.snapshots) - 1

        self._menu.entryconfigure("Отменить", state="normal" if can_undo else "disabled")
        self._menu.entryconfigure("Повторить", state="normal" if can_redo else "disabled")
        self._menu.entryconfigure("Вырезать", state="normal" if has_selection else "disabled")
        self._menu.entryconfigure("Копировать", state="normal" if has_selection else "disabled")

    def _show_menu_from_keyboard(self, event: tk.Event) -> str:
        entry = self._get_entry_widget(event.widget)
        if entry is None:
            return "break"

        entry.focus_set()
        self._update_menu_state(entry)

        x = entry.winfo_rootx() + 16
        y = entry.winfo_rooty() + min(entry.winfo_height(), 24)

        try:
            self._menu.tk_popup(x, y)
        finally:
            self._menu.grab_release()

        return "break"


    def _on_focus_in(self, event: tk.Event) -> None:
        entry = self._get_entry_widget(event.widget)
        if entry is None:
            return
        self._reset_history(entry)

    def _schedule_record(self, entry: EntryWidget) -> None:
        entry.after_idle(lambda: self._record_state(entry))

    def _record_state(self, entry: EntryWidget) -> None:
        if not entry.winfo_exists():
            return

        if entry in self._suspended_widgets:
            return

        history = self._ensure_history(entry)
        current_value = entry.get()

        if history.snapshots and history.snapshots[history.index] == current_value:
            return

        if history.index < len(history.snapshots) - 1:
            history.snapshots = history.snapshots[: history.index + 1]

        history.snapshots.append(current_value)
        history.index = len(history.snapshots) - 1

        max_depth = 100
        if len(history.snapshots) > max_depth:
            overflow = len(history.snapshots) - max_depth
            history.snapshots = history.snapshots[overflow:]
            history.index = max(0, history.index - overflow)

    def _ensure_history(self, entry: EntryWidget) -> _EntryHistory:
        history = self._histories.get(entry)
        if history is None:
            history = _EntryHistory(snapshots=[entry.get()], index=0)
            self._histories[entry] = history
        return history

    def _reset_history(self, entry: EntryWidget) -> None:
        self._histories[entry] = _EntryHistory(snapshots=[entry.get()], index=0)

    def _replace_text(self, entry: EntryWidget, value: str) -> None:
        self._suspended_widgets.add(entry)
        try:
            entry.delete(0, "end")
            entry.insert(0, value)
            entry.icursor("end")
            entry.xview("moveto", 1.0)
        finally:
            self._suspended_widgets.discard(entry)

    def _get_entry_widget(self, widget: object) -> EntryWidget | None:
        if isinstance(widget, (tk.Entry, ttk.Entry)):
            return cast(EntryWidget, widget)
        return None