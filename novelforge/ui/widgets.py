"""
Small reusable widgets.

Nothing decorative. The scrollable form is the only non-obvious piece: Tk has
no native scrolling container, so it is a Canvas with a Frame inside whose
scrollregion tracks the frame's size.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


class ScrollFrame(ttk.Frame):
    """A vertically scrollable container. Add children to `.body`."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.body = ttk.Frame(self.canvas)

        self._window = self.canvas.create_window(
            (0, 0), window=self.body, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Bind the wheel only while the pointer is inside, so the editor keeps
        # its own scrolling.
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_body_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)

    def _bind_wheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def clear(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    def scroll_to_top(self) -> None:
        self.canvas.yview_moveto(0)


class ScrolledText(ttk.Frame):
    """Text widget with a vertical scrollbar and sane editing defaults."""

    def __init__(self, master, height: int = 10, wrap: str = "word",
                 font: Optional[Tuple] = None, **kwargs) -> None:
        super().__init__(master)
        self.text = tk.Text(
            self, height=height, wrap=wrap, undo=True, maxundo=-1,
            autoseparators=True, borderwidth=0, highlightthickness=0,
            padx=10, pady=8, **kwargs
        )
        if font:
            self.text.configure(font=font)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.text.yview
        )
        self.text.configure(yscrollcommand=self.scrollbar.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def get_value(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_value(self, value: str, keep_undo: bool = False) -> None:
        state = self.text.cget("state")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        if value:
            self.text.insert("1.0", value)
        if not keep_undo:
            self.text.edit_reset()
        self.text.edit_modified(False)
        self.text.configure(state=state)

    def set_readonly(self, readonly: bool) -> None:
        self.text.configure(state="disabled" if readonly else "normal")


class Form:
    """
    A label-plus-input form bound to an object's attributes.

    `commit()` writes every field back and returns True if anything changed,
    which the caller uses to decide whether to mark the project dirty.
    """

    def __init__(self, parent: ttk.Frame) -> None:
        self.parent = parent
        self.rows: List[Dict[str, Any]] = []
        self._row_index = 0
        parent.columnconfigure(1, weight=1)

    # -- construction ---------------------------------------------------
    def heading(self, text: str) -> None:
        label = ttk.Label(self.parent, text=text.upper(), style="Section.TLabel")
        label.grid(row=self._row_index, column=0, columnspan=2,
                   sticky="w", pady=(14, 4), padx=(2, 6))
        self._row_index += 1

    def hint(self, text: str) -> None:
        label = ttk.Label(self.parent, text=text, style="Hint.TLabel",
                          wraplength=300, justify="left")
        label.grid(row=self._row_index, column=0, columnspan=2,
                   sticky="w", pady=(0, 6), padx=(2, 6))
        self._row_index += 1

    def entry(self, label: str, obj: Any, attr: str,
              width: int = 28) -> ttk.Entry:
        var = tk.StringVar(value=str(getattr(obj, attr, "") or ""))
        self._label(label)
        widget = ttk.Entry(self.parent, textvariable=var, width=width)
        widget.grid(row=self._row_index, column=1, sticky="ew",
                    padx=(4, 6), pady=1)
        self._row_index += 1
        self.rows.append({"kind": "str", "var": var, "obj": obj, "attr": attr})
        return widget

    def integer(self, label: str, obj: Any, attr: str,
                width: int = 12) -> ttk.Entry:
        var = tk.StringVar(value=str(getattr(obj, attr, 0) or 0))
        self._label(label)
        widget = ttk.Entry(self.parent, textvariable=var, width=width)
        widget.grid(row=self._row_index, column=1, sticky="w",
                    padx=(4, 6), pady=1)
        self._row_index += 1
        self.rows.append({"kind": "int", "var": var, "obj": obj, "attr": attr})
        return widget

    def combo(self, label: str, obj: Any, attr: str,
              values: Sequence[str], width: int = 26) -> ttk.Combobox:
        var = tk.StringVar(value=str(getattr(obj, attr, "") or ""))
        self._label(label)
        widget = ttk.Combobox(self.parent, textvariable=var,
                              values=list(values), width=width, state="readonly")
        widget.grid(row=self._row_index, column=1, sticky="ew",
                    padx=(4, 6), pady=1)
        self._row_index += 1
        self.rows.append({"kind": "str", "var": var, "obj": obj, "attr": attr})
        return widget

    def check(self, label: str, obj: Any, attr: str) -> ttk.Checkbutton:
        var = tk.BooleanVar(value=bool(getattr(obj, attr, False)))
        widget = ttk.Checkbutton(self.parent, text=label, variable=var)
        widget.grid(row=self._row_index, column=0, columnspan=2,
                    sticky="w", padx=(2, 6), pady=1)
        self._row_index += 1
        self.rows.append({"kind": "bool", "var": var, "obj": obj, "attr": attr})
        return widget

    def multiline(self, label: str, obj: Any, attr: str,
                  height: int = 3) -> tk.Text:
        self._label(label, top=True)
        widget = tk.Text(self.parent, height=height, wrap="word", undo=True,
                         borderwidth=1, relief="solid", highlightthickness=0,
                         padx=4, pady=3)
        value = str(getattr(obj, attr, "") or "")
        if value:
            widget.insert("1.0", value)
        widget.grid(row=self._row_index, column=1, sticky="ew",
                    padx=(4, 6), pady=2)
        self._row_index += 1
        self.rows.append({"kind": "text", "widget": widget,
                          "obj": obj, "attr": attr})
        return widget

    def picker(self, label: str, obj: Any, attr: str,
               options: Sequence[Tuple[str, str]],
               allow_blank: str = "(none)") -> ttk.Combobox:
        """
        A combo mapping display names to ids - for POV, location, etc.

        `options` is [(id, display), ...].
        """
        lookup = {display: ident for ident, display in options}
        reverse = {ident: display for ident, display in options}
        if allow_blank:
            lookup[allow_blank] = ""
        current = reverse.get(getattr(obj, attr, ""), allow_blank)
        var = tk.StringVar(value=current)
        self._label(label)
        values = ([allow_blank] if allow_blank else []) + [d for _i, d in options]
        widget = ttk.Combobox(self.parent, textvariable=var, values=values,
                              width=26, state="readonly")
        widget.grid(row=self._row_index, column=1, sticky="ew",
                    padx=(4, 6), pady=1)
        self._row_index += 1
        self.rows.append({"kind": "map", "var": var, "obj": obj,
                          "attr": attr, "lookup": lookup})
        return widget

    def multipicker(self, label: str, obj: Any, attr: str,
                    options: Sequence[Tuple[str, str]],
                    height: int = 5) -> tk.Listbox:
        """Multi-select list bound to a list-of-ids attribute."""
        self._label(label, top=True)
        frame = ttk.Frame(self.parent)
        frame.grid(row=self._row_index, column=1, sticky="ew", padx=(4, 6), pady=2)
        listbox = tk.Listbox(frame, selectmode="extended",
                            height=min(height, max(2, len(options))),
                            exportselection=False, activestyle="none",
                            borderwidth=1, relief="solid", highlightthickness=0)
        listbox.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        # Only five rows are visible. A cast of twenty characters means the
        # rest were simply unreachable without this - the list scrolled with
        # the keyboard but nothing on screen said so, or let the mouse do it.
        if len(options) > height:
            bar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
            bar.grid(row=0, column=1, sticky="ns")
            listbox.configure(yscrollcommand=bar.set)
        ids = [ident for ident, _d in options]
        for _ident, display in options:
            listbox.insert("end", display)
        selected = set(getattr(obj, attr, []) or [])
        for index, ident in enumerate(ids):
            if ident in selected:
                listbox.selection_set(index)
        self._row_index += 1
        self.rows.append({"kind": "multi", "widget": listbox, "obj": obj,
                          "attr": attr, "ids": ids})
        return listbox

    def button_row(self, buttons: Sequence[Tuple[str, Callable[[], None]]]) -> None:
        frame = ttk.Frame(self.parent)
        frame.grid(row=self._row_index, column=0, columnspan=2,
                   sticky="ew", pady=(10, 2), padx=2)
        for index, (text, command) in enumerate(buttons):
            ttk.Button(frame, text=text, command=command).grid(
                row=0, column=index, padx=(0, 4), sticky="w"
            )
        self._row_index += 1

    def readonly(self, label: str, value: str) -> None:
        self._label(label)
        widget = ttk.Label(self.parent, text=value, style="Value.TLabel",
                           wraplength=280, justify="left")
        widget.grid(row=self._row_index, column=1, sticky="w",
                    padx=(4, 6), pady=1)
        self._row_index += 1

    def separator(self) -> None:
        ttk.Separator(self.parent, orient="horizontal").grid(
            row=self._row_index, column=0, columnspan=2,
            sticky="ew", pady=8, padx=2
        )
        self._row_index += 1

    def _label(self, text: str, top: bool = False) -> None:
        ttk.Label(self.parent, text=text, style="Field.TLabel",
                  wraplength=130, justify="left").grid(
            row=self._row_index, column=0,
            sticky="nw" if top else "w", padx=(2, 2), pady=(3 if top else 2, 1)
        )

    # -- commit ---------------------------------------------------------
    def commit(self) -> bool:
        """Write every field back to its object. True if anything changed."""
        changed = False
        for row in self.rows:
            obj, attr, kind = row["obj"], row["attr"], row["kind"]
            old = getattr(obj, attr, None)

            if kind == "str":
                new: Any = row["var"].get().strip()
            elif kind == "int":
                raw = row["var"].get().strip().replace(",", "")
                try:
                    new = int(float(raw)) if raw else 0
                except ValueError:
                    new = old if isinstance(old, int) else 0
            elif kind == "bool":
                new = bool(row["var"].get())
            elif kind == "text":
                new = row["widget"].get("1.0", "end-1c").strip()
            elif kind == "map":
                new = row["lookup"].get(row["var"].get(), "")
            elif kind == "multi":
                listbox = row["widget"]
                ids = row["ids"]
                new = [ids[i] for i in listbox.curselection()]
            else:
                continue

            if new != old:
                setattr(obj, attr, new)
                changed = True
        return changed


class StatusBar(ttk.Frame):
    """Bottom bar: transient message on the left, live counters on the right."""

    def __init__(self, master) -> None:
        super().__init__(master, padding=(8, 3))
        self.message = ttk.Label(self, text="", anchor="w", style="Status.TLabel")
        self.message.grid(row=0, column=0, sticky="ew")
        self.counters = ttk.Label(self, text="", anchor="e", style="Status.TLabel")
        self.counters.grid(row=0, column=1, sticky="e")
        self.columnconfigure(0, weight=1)
        self._clear_job: Optional[str] = None

    def say(self, text: str, seconds: float = 6.0) -> None:
        self.message.configure(text=text)
        if self._clear_job:
            try:
                self.after_cancel(self._clear_job)
            except (ValueError, tk.TclError):
                pass
            self._clear_job = None
        if seconds:
            self._clear_job = self.after(
                int(seconds * 1000), lambda: self.message.configure(text="")
            )

    def set_counters(self, text: str) -> None:
        self.counters.configure(text=text)


# ==========================================================================
# Window sizing
# ==========================================================================
#
# Every window in the application is sized through here, and the rule is the
# same everywhere: a window may never open larger than the desktop actually
# available, and may never open anywhere the title bar or the buttons cannot
# be reached.
#
# The old version of this asked Tk for the screen size and used it directly.
# That is wrong twice over. winfo_screenheight() includes the taskbar, so a
# window sized to it always has its bottom edge - which is where the buttons
# live - hidden. And nothing clamped the requested size, so a window asking
# for 1440x900 opened at 1440x900 on a 1366x768 laptop with a quarter of it
# off the screen. That is the "I have to maximise and resize before I can
# click anything" problem.

#: Cached work area, so a hundred dialogs do not each make a system call.
_WORK_AREA: Optional[Tuple[int, int, int, int]] = None

#: Breathing room left around a clamped window so it never looks wedged in.
_EDGE_MARGIN = 16


def screen_work_area(window: tk.Misc) -> Tuple[int, int, int, int]:
    """
    The usable desktop as (x, y, width, height) - the screen minus the taskbar.

    Windows reports this properly through SPI_GETWORKAREA, which also handles
    a taskbar docked to the side or the top. Anywhere else, or if the call
    fails, fall back to the full screen less a taskbar-sized strip: too
    cautious by a few pixels is survivable, too generous is not.
    """
    global _WORK_AREA
    if _WORK_AREA is not None:
        return _WORK_AREA

    area: Optional[Tuple[int, int, int, int]] = None
    try:
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        # SPI_GETWORKAREA = 0x0030
        if ctypes.windll.user32.SystemParametersInfoW(
            0x0030, 0, ctypes.byref(rect), 0
        ):
            area = (rect.left, rect.top,
                    rect.right - rect.left, rect.bottom - rect.top)
    except Exception:
        area = None

    if not area or area[2] < 320 or area[3] < 240:
        area = (0, 0,
                window.winfo_screenwidth(),
                max(240, window.winfo_screenheight() - 64))

    _WORK_AREA = area
    return area


def reset_work_area() -> None:
    """Forget the cached measurements - used by the tests, and on a DPI change."""
    global _WORK_AREA, _CHROME
    _WORK_AREA = None
    _CHROME = None


#: Width and height the window manager adds around the client area.
_CHROME: Optional[Tuple[int, int]] = None


def window_chrome(window: tk.Misc) -> Tuple[int, int]:
    """
    How much bigger a window is than the size we ask for.

    geometry("1350x704") sets the *client* area. Windows then draws a title
    bar and a border around it, so the thing actually on screen is about 39
    pixels taller and 16 wider. Clamping to the work area without allowing for
    that leaves the bottom edge - and every OK button on it - under the
    taskbar, which is precisely the bug this whole module exists to kill.
    """
    global _CHROME
    if _CHROME is not None:
        return _CHROME

    chrome = (16, 40)
    try:
        import ctypes

        metric = ctypes.windll.user32.GetSystemMetrics
        caption = metric(4)          # SM_CYCAPTION
        frame_x = metric(32)         # SM_CXSIZEFRAME
        frame_y = metric(33)         # SM_CYSIZEFRAME
        padded = metric(92)          # SM_CXPADDEDBORDER
        border_x = frame_x + padded
        border_y = frame_y + padded
        if caption > 0 and border_x >= 0:
            chrome = (2 * border_x, caption + 2 * border_y)
    except Exception:
        pass

    _CHROME = chrome
    return chrome


def menu_bar_height(window: tk.Misc) -> int:
    """
    Extra height a menu bar costs, which the requested size does not include.

    Tk's geometry for a toplevel with a menu bar covers the area *below* the
    menu, so the window Windows actually draws is one menu row taller than
    asked for. Only the main window has one, and it is the window most likely
    to be sized to fill the screen - so without this it is exactly the window
    that ends up under the taskbar.
    """
    try:
        if not window.cget("menu"):
            return 0
    except (tk.TclError, AttributeError):
        return 0
    try:
        from tkinter import font as tkfont

        return tkfont.nametofont("TkMenuFont", root=window).metrics(
            "linespace") + 8
    except Exception:
        return 26


def usable_area(window: tk.Misc) -> Tuple[int, int, int, int]:
    """Work area reduced by the window frame - what a client area may fill."""
    left, top, work_w, work_h = screen_work_area(window)
    chrome_w, chrome_h = window_chrome(window)
    chrome_h += menu_bar_height(window)
    return (left, top,
            max(320, work_w - chrome_w - _EDGE_MARGIN),
            max(240, work_h - chrome_h - _EDGE_MARGIN))


def fit_size(window: tk.Misc, width: int, height: int) -> Tuple[int, int]:
    """Shrink a requested size to something that actually fits on screen."""
    _x, _y, room_w, room_h = usable_area(window)
    return (max(320, min(int(width), room_w)),
            max(240, min(int(height), room_h)))


def center_window(window: tk.Misc, width: int, height: int,
                  min_width: int = 0, min_height: int = 0) -> None:
    """
    Size, clamp and centre a window inside the usable desktop.

    Also sets a minimum size, itself clamped, so a window can never be dragged
    smaller than the screen can show but also never demands more than exists -
    a minsize larger than the desktop is unfixable by the user.
    """
    window.update_idletasks()

    left, top, work_w, work_h = screen_work_area(window)
    chrome_w, chrome_h = window_chrome(window)
    chrome_h += menu_bar_height(window)
    width, height = fit_size(window, width, height)

    # Centre and clamp the *outer* window, frame and menu bar included.
    outer_w, outer_h = width + chrome_w, height + chrome_h
    x = left + max(0, (work_w - outer_w) // 2)
    y = top + max(0, (work_h - outer_h) // 2)
    x = max(left, min(x, left + work_w - outer_w))
    y = max(top, min(y, top + work_h - outer_h))

    window.geometry(f"{width}x{height}+{x}+{y}")

    if min_width or min_height:
        floor_w = min(min_width or width, width)
        floor_h = min(min_height or height, height)
        try:
            window.minsize(floor_w, floor_h)
        except tk.TclError:
            pass


def _parse_geometry(geometry: str) -> Optional[Tuple[int, int, int, int]]:
    """(width, height, x, y) from "WxH+X+Y", or None if it is not that."""
    import re

    match = re.match(r"^(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)$",
                     (geometry or "").strip())
    if not match:
        return None

    def offset(raw: str) -> Optional[int]:
        # Tk writes a negative coordinate as "+-68". A bare leading "-" means
        # something else entirely - offset from the right or bottom edge -
        # which is not worth reconstructing, so those are refused.
        return int(raw[1:]) if raw.startswith("+") else None

    x, y = offset(match.group(3)), offset(match.group(4))
    if x is None or y is None:
        return None
    return int(match.group(1)), int(match.group(2)), x, y


def clamp_to_screen(window: tk.Misc, geometry: str) -> str:
    """
    Make a remembered "WxH+X+Y" safe to reuse.

    A geometry saved on a second monitor, or before the taskbar moved, will
    otherwise restore the window somewhere the user cannot reach it. Rather
    than discard the memory, pull it back onto the visible desktop.
    """
    parsed = _parse_geometry(geometry)
    if not parsed:
        return ""
    width, height, x, y = parsed

    left, top, work_w, work_h = screen_work_area(window)
    chrome_w, chrome_h = window_chrome(window)
    chrome_h += menu_bar_height(window)
    width, height = fit_size(window, width, height)
    x = max(left, min(x, left + work_w - width - chrome_w))
    y = max(top, min(y, top + work_h - height - chrome_h))
    return f"{width}x{height}+{x}+{y}"


def add_editing_keys(text: tk.Text) -> None:
    """
    The editing shortcuts every other text editor has and Tk does not.

    Tk already provides word navigation with Ctrl+Left/Right, Home and End,
    Ctrl+Home/End, every Shift selection, double-click for a word and
    Ctrl+Z/Y. What it has never had is word deletion, line operations and
    case changes - the things a writer reaches for without thinking, and
    notices immediately when they do nothing.

    Every one of these is wrapped in an undo separator so a single Ctrl+Z
    takes back the whole operation rather than a character at a time.
    """

    def edit(fn):
        """Run an operation as one undoable step."""
        def wrapped(event=None):
            text.edit_separator()
            try:
                fn()
            except tk.TclError:
                pass
            text.edit_separator()
            return "break"
        return wrapped

    # -- word deletion ---------------------------------------------------
    def delete_word_left() -> None:
        if text.tag_ranges("sel"):
            text.delete("sel.first", "sel.last")
            return
        start = text.index("insert -1c wordstart")
        # Sitting just after a space, wordstart lands on the space itself;
        # step back again so the word actually goes.
        if text.get(start, "insert").strip() == "":
            start = text.index(f"{start} -1c wordstart")
        text.delete(start, "insert")

    def delete_word_right() -> None:
        if text.tag_ranges("sel"):
            text.delete("sel.first", "sel.last")
            return
        end = text.index("insert wordend")
        if text.get("insert", end).strip() == "":
            end = text.index(f"{end} +1c wordend")
        text.delete("insert", end)

    # -- line operations -------------------------------------------------
    def line_bounds() -> Tuple[str, str]:
        return text.index("insert linestart"), text.index("insert lineend")

    def duplicate_line() -> None:
        start, end = line_bounds()
        body = text.get(start, end)
        text.insert(end, "\n" + body)
        text.mark_set("insert", f"{end} +1c lineend")

    def delete_line() -> None:
        start = text.index("insert linestart")
        end = text.index("insert lineend +1c")
        text.delete(start, end)

    def move_line(delta: int) -> None:
        line = int(text.index("insert").split(".")[0])
        column = text.index("insert").split(".")[1]
        target = line + delta
        last = int(text.index("end-1c").split(".")[0])
        if target < 1 or target > last:
            return
        body = text.get(f"{line}.0", f"{line}.end")
        other = text.get(f"{target}.0", f"{target}.end")
        text.delete(f"{line}.0", f"{line}.end")
        text.insert(f"{line}.0", other)
        text.delete(f"{target}.0", f"{target}.end")
        text.insert(f"{target}.0", body)
        text.mark_set("insert", f"{target}.{column}")
        text.see("insert")

    def join_lines() -> None:
        end = text.index("insert lineend")
        if text.compare(end, ">=", "end-1c"):
            return
        text.delete(end, f"{end} +1c")
        # Leave exactly one space where the break was, unless there already
        # is one - joining should not produce "word  word".
        if text.get(f"{end} -1c", end) not in (" ", "") and \
                text.get(end, f"{end} +1c") != " ":
            text.insert(end, " ")

    # -- selection -------------------------------------------------------
    def select_paragraph(event=None):
        start = text.search(r"^\s*$", "insert", backwards=True,
                            regexp=True) or "1.0"
        if start != "1.0":
            start = text.index(f"{start} +1l linestart")
        end = text.search(r"^\s*$", "insert", regexp=True) or "end-1c"
        text.tag_remove("sel", "1.0", "end")
        text.tag_add("sel", start, end)
        text.mark_set("insert", end)
        return "break"

    def select_line(event=None):
        text.tag_remove("sel", "1.0", "end")
        text.tag_add("sel", "insert linestart", "insert lineend")
        return "break"

    # -- case ------------------------------------------------------------
    def recase(fn) -> None:
        if not text.tag_ranges("sel"):
            text.tag_add("sel", "insert wordstart", "insert wordend")
        if not text.tag_ranges("sel"):
            return
        start, end = text.index("sel.first"), text.index("sel.last")
        body = text.get(start, end)
        text.delete(start, end)
        text.insert(start, fn(body))
        text.tag_add("sel", start, f"{start} +{len(body)}c")

    def sentence_case(body: str) -> str:
        import re as _re

        lowered = body.lower()
        # Capitalise the first letter, and the first after . ! ? and a break.
        return _re.sub(r"(^|[.!?]\s+|\n\s*)([a-z])",
                       lambda m: m.group(1) + m.group(2).upper(), lowered)

    bindings = {
        "<Control-BackSpace>": edit(delete_word_left),
        "<Control-Delete>": edit(delete_word_right),
        "<Control-d>": edit(duplicate_line),
        "<Control-Shift-K>": edit(delete_line),
        "<Alt-Up>": edit(lambda: move_line(-1)),
        "<Alt-Down>": edit(lambda: move_line(1)),
        "<Control-j>": edit(join_lines),
        "<Control-Shift-U>": edit(lambda: recase(str.upper)),
        "<Control-Shift-L>": edit(lambda: recase(str.lower)),
        "<Control-Shift-T>": edit(lambda: recase(str.title)),
        "<Control-Shift-S>": edit(lambda: recase(sentence_case)),
        "<Control-l>": select_line,
        "<Control-Shift-P>": select_paragraph,
    }
    for sequence, handler in bindings.items():
        text.bind(sequence, handler)

    # Triple click selects the paragraph, not just the visual line, because a
    # paragraph is the unit a novelist actually works in.
    text.bind("<Triple-Button-1>", lambda e: (text.after_idle(select_paragraph),
                                              None)[1])


def bind_tree_shortcuts(tree: ttk.Treeview) -> None:
    """Type-to-find inside a Treeview, which Tk does not give you."""
    state = {"buffer": "", "when": 0.0}

    def on_key(event: tk.Event) -> None:
        import time

        char = event.char
        if not char or not char.isprintable():
            return
        now = time.time()
        if now - state["when"] > 1.2:
            state["buffer"] = ""
        state["when"] = now
        state["buffer"] += char.lower()
        needle = state["buffer"]

        def walk(node: str = "") -> Optional[str]:
            for child in tree.get_children(node):
                text = str(tree.item(child, "text")).strip().lower()
                if text.startswith(needle):
                    return child
                found = walk(child)
                if found:
                    return found
            return None

        match = walk()
        if match:
            tree.see(match)
            tree.selection_set(match)

    tree.bind("<Key>", on_key, add="+")
