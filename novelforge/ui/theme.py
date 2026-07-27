"""
Visual design system.

Two layers, deliberately separated:

  * **Widget chrome** comes from the Sun Valley ttk theme (sv-ttk), which gives
    buttons, entries, scrollbars, checkboxes and comboboxes a genuine Windows 11
    appearance. Restyling those by hand in ttk is possible but never looks
    right, because their shapes are drawn from theme images.

  * **Content surfaces** - the editor, the binder, every Canvas - use the
    palette here. Those are the areas the app fully controls, and they are what
    the writer actually looks at for hours, so they get warmer, lower-contrast
    colours than a stock UI theme would.

Everything below is defined once and referenced by name. Hard-coded colours
scattered through UI code are the single biggest reason software looks cheap.
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Dict, List, Optional, Sequence, Tuple

# ==========================================================================
# Palettes
#
# Surfaces are numbered by elevation: surface_0 is the window, surface_1 a
# panel, surface_2 a raised card. Text has three weights. Every foreground is
# checked against its background for WCAG AA (4.5:1 for body text).
# ==========================================================================

PALETTES: Dict[str, Dict[str, str]] = {
    "light": {
        "base": "light",
        "surface_0": "#f3f3f1",
        "surface_1": "#fbfbfa",
        "surface_2": "#ffffff",
        "surface_sunken": "#ececea",
        "page": "#ffffff",          # the writing surface
        "text": "#1c1b19",
        "text_muted": "#5f5d59",
        "text_faint": "#8b8884",
        "border": "#dcdad6",
        "border_strong": "#c3c0ba",
        "accent": "#2f6f8f",
        "accent_text": "#ffffff",
        "accent_soft": "#dbe9f0",
        "selection": "#cfe3ee",
        "caret": "#1c1b19",
        "success": "#3f7d52",
        "warning": "#a8721f",
        "danger": "#a8433a",
        "info": "#3a6ea5",
    },
    "dark": {
        "base": "dark",
        "surface_0": "#1a1c1e",
        "surface_1": "#212427",
        "surface_2": "#2a2d31",
        "surface_sunken": "#151719",
        "page": "#1e2124",
        "text": "#e6e3dd",
        "text_muted": "#a5a19a",
        "text_faint": "#75716b",
        "border": "#33373b",
        "border_strong": "#454a4f",
        "accent": "#6fa8c8",
        "accent_text": "#12161a",
        "accent_soft": "#26343d",
        "selection": "#33454f",
        "caret": "#e6e3dd",
        "success": "#71a883",
        "warning": "#d0a04e",
        "danger": "#d1786d",
        "info": "#7fa8d4",
    },
    # A warm paper mode for long drafting sessions. Built on the light base so
    # the widget chrome still matches, with the content surfaces shifted amber.
    "sepia": {
        "base": "light",
        "surface_0": "#efe7d8",
        "surface_1": "#f7f1e4",
        "surface_2": "#fdf8ee",
        "surface_sunken": "#e6dcc9",
        "page": "#fbf4e4",
        "text": "#2e2419",
        "text_muted": "#6b5c47",
        # Darkened from #97876e, which measured 2.85:1 against the sepia
        # surface and failed the 3:1 floor for secondary text.
        "text_faint": "#877759",
        "border": "#ddd0b8",
        "border_strong": "#c6b596",
        "accent": "#8a5a2b",
        "accent_text": "#fdf8ee",
        "accent_soft": "#ecdfc6",
        "selection": "#e3d3b2",
        "caret": "#2e2419",
        "success": "#4f7a45",
        "warning": "#9a6f1e",
        "danger": "#9c4436",
        "info": "#4a6b8a",
    },
    # Maximum contrast, for low vision or bright rooms.
    "contrast": {
        "base": "dark",
        "surface_0": "#000000",
        "surface_1": "#0b0b0b",
        "surface_2": "#161616",
        "surface_sunken": "#000000",
        "page": "#000000",
        "text": "#ffffff",
        "text_muted": "#e0e0e0",
        "text_faint": "#b8b8b8",
        "border": "#5a5a5a",
        "border_strong": "#8a8a8a",
        "accent": "#4cc2ff",
        "accent_text": "#000000",
        "accent_soft": "#10303d",
        "selection": "#1f4d61",
        "caret": "#ffffff",
        "success": "#5ddb84",
        "warning": "#ffd166",
        "danger": "#ff7b6b",
        "info": "#7cc7ff",
    },
}

THEME_LABELS = {
    "light": "Light",
    "dark": "Dark",
    "sepia": "Sepia (warm paper)",
    "contrast": "High contrast",
}

# Scene status colours, per theme, so they stay legible on every background.
STATUS_TINTS: Dict[str, Dict[str, str]] = {
    "light": {
        "Outline": "#8b8884", "Draft": "#a8721f", "Revised": "#3a6ea5",
        "Needs Work": "#a8433a", "Final": "#3f7d52",
    },
    "dark": {
        "Outline": "#8f8b84", "Draft": "#d0a04e", "Revised": "#7fa8d4",
        "Needs Work": "#d1786d", "Final": "#71a883",
    },
    "sepia": {
        "Outline": "#97876e", "Draft": "#9a6f1e", "Revised": "#4a6b8a",
        "Needs Work": "#9c4436", "Final": "#4f7a45",
    },
    "contrast": {
        "Outline": "#c8c8c8", "Draft": "#ffd166", "Revised": "#7cc7ff",
        "Needs Work": "#ff7b6b", "Final": "#5ddb84",
    },
}

# ==========================================================================
# Type and spacing scales
# ==========================================================================

# One scale, used everywhere. Sizes that drift produce the "assembled from
# parts" look; a fixed ratio reads as designed.
TYPE_SCALE = {
    "display": 22,
    "title": 15,
    "heading": 11,
    "body": 10,
    "small": 9,
    "tiny": 8,
}

# 4px base grid. Layout code refers to these, never to raw numbers.
SPACE = {"xs": 2, "sm": 4, "md": 8, "lg": 12, "xl": 18, "xxl": 28}

UI_FONT_CANDIDATES = ["Segoe UI Variable Text", "Segoe UI", "Inter",
                      "Calibri", "Helvetica"]
MONO_FONT_CANDIDATES = ["Cascadia Code", "Cascadia Mono", "Consolas",
                        "JetBrains Mono", "Courier New"]
PROSE_FONT_CANDIDATES = ["Georgia", "Cambria", "Constantia", "Palatino Linotype",
                         "Iowan Old Style", "Times New Roman"]


def _first_available(candidates: Sequence[str], fallback: str) -> str:
    try:
        families = set(tkfont.families())
    except (tk.TclError, RuntimeError):
        return fallback
    for name in candidates:
        if name in families:
            return name
    return fallback


class Fonts:
    """Resolved font families. Built once a Tk root exists."""

    def __init__(self) -> None:
        self.ui = _first_available(UI_FONT_CANDIDATES, "Segoe UI")
        self.mono = _first_available(MONO_FONT_CANDIDATES, "Consolas")
        self.prose = _first_available(PROSE_FONT_CANDIDATES, "Georgia")

    def at(self, size_key: str, weight: str = "normal",
           slant: str = "roman") -> tuple:
        return (self.ui, TYPE_SCALE.get(size_key, 10), weight) \
            if slant == "roman" else (self.ui, TYPE_SCALE.get(size_key, 10),
                                      weight, slant)


_fonts: Optional[Fonts] = None


def fonts() -> Fonts:
    global _fonts
    if _fonts is None:
        _fonts = Fonts()
    return _fonts


# ==========================================================================
# Applying a theme
# ==========================================================================

_current = "light"


def current() -> str:
    return _current


def palette(mode: Optional[str] = None) -> Dict[str, str]:
    return PALETTES.get(mode or _current, PALETTES["light"])


def status_colour(status: str, mode: Optional[str] = None) -> str:
    tints = STATUS_TINTS.get(mode or _current, STATUS_TINTS["light"])
    return tints.get(status, palette(mode)["text_faint"])


def apply(root: tk.Misc, mode: str = "light") -> Dict[str, str]:
    """
    Put a theme on the whole application. Returns the active palette.

    Safe to call repeatedly - switching themes at runtime goes through here.
    """
    global _current
    if mode not in PALETTES:
        mode = "light"
    _current = mode
    colours = PALETTES[mode]
    f = fonts()

    # -- widget chrome ------------------------------------------------
    try:
        import sv_ttk

        sv_ttk.set_theme(colours["base"], root=root)
    except Exception:
        # sv-ttk is optional. Without it the app still works, just plainer.
        try:
            ttk.Style(root).theme_use("vista")
        except tk.TclError:
            pass

    style = ttk.Style(root)

    # Default fonts for the whole app, so nothing inherits Tk's 1990s default.
    for name, spec in (
        ("TkDefaultFont", (f.ui, TYPE_SCALE["body"])),
        ("TkTextFont", (f.ui, TYPE_SCALE["body"])),
        ("TkMenuFont", (f.ui, TYPE_SCALE["body"])),
        ("TkHeadingFont", (f.ui, TYPE_SCALE["heading"], "bold")),
        ("TkTooltipFont", (f.ui, TYPE_SCALE["small"])),
        ("TkFixedFont", (f.mono, TYPE_SCALE["body"])),
    ):
        try:
            named = tkfont.nametofont(name)
            named.configure(family=spec[0], size=spec[1],
                            weight=spec[2] if len(spec) > 2 else "normal")
        except tk.TclError:
            pass

    try:
        root.configure(background=colours["surface_0"])
    except tk.TclError:
        pass

    # -- our own named styles -----------------------------------------
    style.configure("TFrame", background=colours["surface_0"])
    style.configure("Panel.TFrame", background=colours["surface_1"])
    style.configure("Card.TFrame", background=colours["surface_2"],
                    relief="flat")
    style.configure("Toolbar.TFrame", background=colours["surface_1"])

    style.configure("TLabel", background=colours["surface_0"],
                    foreground=colours["text"], font=(f.ui, TYPE_SCALE["body"]))
    style.configure("Panel.TLabel", background=colours["surface_1"],
                    foreground=colours["text"])
    style.configure("Display.TLabel", background=colours["surface_0"],
                    foreground=colours["text"],
                    font=(f.ui, TYPE_SCALE["display"], "bold"))
    style.configure("Title.TLabel", background=colours["surface_0"],
                    foreground=colours["text"],
                    font=(f.ui, TYPE_SCALE["title"], "bold"))
    style.configure("Section.TLabel", background=colours["surface_0"],
                    foreground=colours["accent"],
                    font=(f.ui, TYPE_SCALE["tiny"], "bold"))
    style.configure("Field.TLabel", background=colours["surface_0"],
                    foreground=colours["text_muted"],
                    font=(f.ui, TYPE_SCALE["small"]))
    style.configure("Value.TLabel", background=colours["surface_0"],
                    foreground=colours["text"],
                    font=(f.ui, TYPE_SCALE["small"]))
    style.configure("Hint.TLabel", background=colours["surface_0"],
                    foreground=colours["text_faint"],
                    font=(f.ui, TYPE_SCALE["tiny"]))
    style.configure("Status.TLabel", background=colours["surface_1"],
                    foreground=colours["text_muted"],
                    font=(f.ui, TYPE_SCALE["small"]))
    style.configure("Success.TLabel", background=colours["surface_0"],
                    foreground=colours["success"],
                    font=(f.ui, TYPE_SCALE["small"], "bold"))
    style.configure("Danger.TLabel", background=colours["surface_0"],
                    foreground=colours["danger"],
                    font=(f.ui, TYPE_SCALE["small"], "bold"))

    style.configure("Treeview",
                    background=colours["page"],
                    fieldbackground=colours["page"],
                    foreground=colours["text"],
                    borderwidth=0, relief="flat", rowheight=24,
                    font=(f.ui, TYPE_SCALE["body"]))
    style.map("Treeview",
              background=[("selected", colours["selection"])],
              foreground=[("selected", colours["text"])])
    style.configure("Treeview.Heading",
                    background=colours["surface_1"],
                    foreground=colours["text_faint"],
                    font=(f.ui, TYPE_SCALE["tiny"], "bold"),
                    relief="flat", borderwidth=0)

    style.configure("Gauge.Horizontal.TProgressbar",
                    troughcolor=colours["surface_sunken"],
                    background=colours["accent"],
                    borderwidth=0, thickness=5)
    style.configure("Success.Horizontal.TProgressbar",
                    troughcolor=colours["surface_sunken"],
                    background=colours["success"],
                    borderwidth=0, thickness=5)

    style.configure("TSeparator", background=colours["border"])
    style.configure("TNotebook", background=colours["surface_0"],
                    borderwidth=0)
    style.configure("TNotebook.Tab", font=(f.ui, TYPE_SCALE["body"]))

    return colours


def style_text_widget(widget: tk.Text, *, prose: bool = False,
                      mono: bool = False, size: Optional[int] = None,
                      mode: Optional[str] = None) -> None:
    """Apply the content palette to a raw tk.Text, which ttk cannot style."""
    colours = palette(mode)
    f = fonts()
    family = f.prose if prose else (f.mono if mono else f.ui)
    try:
        widget.configure(
            background=colours["page"],
            foreground=colours["text"],
            insertbackground=colours["caret"],
            selectbackground=colours["selection"],
            selectforeground=colours["text"],
            highlightthickness=0, borderwidth=0, relief="flat",
            font=(family, size or TYPE_SCALE["body"]),
            insertwidth=2,
        )
    except tk.TclError:
        pass


def style_listbox(widget: tk.Listbox, mode: Optional[str] = None) -> None:
    colours = palette(mode)
    f = fonts()
    try:
        widget.configure(
            background=colours["page"], foreground=colours["text"],
            selectbackground=colours["selection"],
            selectforeground=colours["text"],
            highlightthickness=1, highlightbackground=colours["border"],
            highlightcolor=colours["accent"],
            borderwidth=0, relief="flat", activestyle="none",
            font=(f.ui, TYPE_SCALE["small"]),
        )
    except tk.TclError:
        pass


def style_canvas(widget: tk.Canvas, sunken: bool = False,
                 mode: Optional[str] = None) -> None:
    colours = palette(mode)
    try:
        widget.configure(
            background=colours["surface_sunken"] if sunken
            else colours["surface_0"],
            highlightthickness=0, borderwidth=0,
        )
    except tk.TclError:
        pass


# ==========================================================================
# Canvas-drawn widgets
#
# ttk cannot produce rounded cards, rings or sparklines. These draw them on a
# Canvas so the app can have modern surfaces without a heavier framework.
# ==========================================================================


def rounded_rect(canvas: tk.Canvas, x0: float, y0: float, x1: float, y1: float,
                 radius: float = 8.0, **kwargs) -> int:
    """
    A rounded rectangle as a smoothed polygon.

    Duplicating the corner points is what makes Tk's spline curve tightly at
    the corners and stay straight along the edges.
    """
    radius = max(0.0, min(radius, abs(x1 - x0) / 2.0, abs(y1 - y0) / 2.0))
    points = [
        x0 + radius, y0, x1 - radius, y0,
        x1, y0, x1, y0 + radius,
        x1, y1 - radius, x1, y1,
        x1 - radius, y1, x0 + radius, y1,
        x0, y1, x0, y1 - radius,
        x0, y0 + radius, x0, y0,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **kwargs)


def card(canvas: tk.Canvas, x0: float, y0: float, x1: float, y1: float,
         radius: float = 10.0, elevated: bool = True,
         accent: Optional[str] = None, mode: Optional[str] = None
         ) -> List[int]:
    """A surface card with an optional soft shadow and accent edge."""
    colours = palette(mode)
    ids: List[int] = []
    if elevated:
        ids.append(rounded_rect(canvas, x0 + 2, y0 + 3, x1 + 2, y1 + 3,
                                radius, fill=colours["surface_sunken"],
                                outline=""))
    ids.append(rounded_rect(canvas, x0, y0, x1, y1, radius,
                            fill=colours["surface_2"],
                            outline=colours["border"], width=1))
    if accent:
        ids.append(canvas.create_rectangle(x0 + 1, y0 + radius * 0.6,
                                           x0 + 4, y1 - radius * 0.6,
                                           fill=accent, outline=""))
    return ids


def progress_ring(canvas: tk.Canvas, cx: float, cy: float, radius: float,
                  fraction: float, width: float = 7.0,
                  colour: Optional[str] = None, label: str = "",
                  mode: Optional[str] = None) -> List[int]:
    """A donut progress indicator - reads far faster than a number."""
    colours = palette(mode)
    fraction = max(0.0, min(1.0, float(fraction)))
    ids = [canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                              outline=colours["surface_sunken"], width=width)]
    if fraction > 0:
        ids.append(canvas.create_arc(
            cx - radius, cy - radius, cx + radius, cy + radius,
            start=90, extent=-359.9 * fraction, style="arc",
            outline=colour or colours["accent"], width=width,
        ))
    if label:
        ids.append(canvas.create_text(
            cx, cy, text=label, fill=colours["text"],
            font=(fonts().ui, max(8, int(radius * 0.52)), "bold"),
        ))
    return ids


def sparkline(canvas: tk.Canvas, x0: float, y0: float, width: float,
              height: float, values: Sequence[float],
              colour: Optional[str] = None, fill: bool = True,
              mode: Optional[str] = None) -> List[int]:
    """A tiny trend chart. Bars, because daily word counts are discrete."""
    colours = palette(mode)
    if not values:
        return []
    peak = max(values) or 1.0
    ids: List[int] = []
    count = len(values)
    slot = width / count
    bar = max(1.0, slot * 0.68)
    line = colour or colours["accent"]
    for index, value in enumerate(values):
        h = (value / peak) * height
        cx = x0 + slot * index + slot / 2.0
        if h <= 0.5:
            ids.append(canvas.create_line(cx - bar / 2, y0 + height,
                                          cx + bar / 2, y0 + height,
                                          fill=colours["border"], width=1))
            continue
        ids.append(canvas.create_rectangle(
            cx - bar / 2, y0 + height - h, cx + bar / 2, y0 + height,
            fill=line if fill else "", outline=line, width=1,
        ))
    return ids


def badge(canvas: tk.Canvas, x: float, y: float, text: str,
          colour: Optional[str] = None, mode: Optional[str] = None
          ) -> List[int]:
    """A small pill label, for counts and statuses."""
    colours = palette(mode)
    f = fonts()
    size = TYPE_SCALE["tiny"]
    pad_x, pad_y = 6, 3
    text_id = canvas.create_text(x + pad_x, y + pad_y, text=text, anchor="nw",
                                 font=(f.ui, size, "bold"),
                                 fill=colours["accent_text"])
    bounds = canvas.bbox(text_id)
    if not bounds:
        return [text_id]
    pill = rounded_rect(canvas, bounds[0] - pad_x, bounds[1] - pad_y,
                        bounds[2] + pad_x, bounds[3] + pad_y,
                        radius=(bounds[3] - bounds[1] + pad_y * 2) / 2.0,
                        fill=colour or colours["accent"], outline="")
    canvas.tag_raise(text_id, pill)
    return [pill, text_id]


def divider(canvas: tk.Canvas, x0: float, y: float, x1: float,
            mode: Optional[str] = None) -> int:
    return canvas.create_line(x0, y, x1, y, fill=palette(mode)["border"],
                              width=1)


# ==========================================================================
# Contrast checking
# ==========================================================================


def _luminance(colour: str) -> float:
    colour = colour.lstrip("#")
    if len(colour) != 6:
        return 0.0
    channels = []
    for i in (0, 2, 4):
        v = int(colour[i:i + 2], 16) / 255.0
        channels.append(v / 12.92 if v <= 0.04045
                        else ((v + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours. 4.5 is the AA body-text floor."""
    la, lb = _luminance(a), _luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def audit_contrast(mode: str) -> List[Tuple[str, str, float]]:
    """
    Every foreground/background pair that fails WCAG AA.

    Used by the test suite: a theme that ships unreadable text is a defect, not
    a matter of taste.
    """
    colours = PALETTES.get(mode, PALETTES["light"])
    checks: List[Tuple[str, str, str, float]] = [
        ("text", "surface_0", "body", 4.5),
        ("text", "surface_1", "body", 4.5),
        ("text", "surface_2", "body", 4.5),
        ("text", "page", "body", 4.5),
        ("text_muted", "surface_0", "body", 4.5),
        ("text_muted", "surface_1", "body", 4.5),
        ("text_faint", "surface_0", "large", 3.0),
        ("accent", "surface_0", "large", 3.0),
        ("accent", "surface_1", "large", 3.0),
        ("accent_text", "accent", "body", 4.5),
        ("success", "surface_0", "large", 3.0),
        ("warning", "surface_0", "large", 3.0),
        ("danger", "surface_0", "large", 3.0),
        ("text", "selection", "body", 4.5),
    ]
    failures: List[Tuple[str, str, float]] = []
    for fg, bg, _kind, minimum in checks:
        ratio = contrast_ratio(colours[fg], colours[bg])
        if ratio < minimum:
            failures.append((f"{fg} on {bg}", f"need {minimum}", round(ratio, 2)))
    for status, tint in STATUS_TINTS.get(mode, {}).items():
        ratio = contrast_ratio(tint, colours["page"])
        if ratio < 3.0:
            failures.append((f"status {status} on page", "need 3.0",
                             round(ratio, 2)))
    return failures
