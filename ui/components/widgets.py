"""Small shared widgets, with explicit layout left to each page."""

from functools import lru_cache
import math
from pathlib import Path
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageOps
from ui import theme as T

ASSETS = Path(__file__).resolve().parents[2] / "assets"
# Uploaded images are decoded once and kept in memory for this offline session.
LOCAL_IMAGES = {}
GLYPHS = {"home": "\ue80f", "cart": "\ue7bf", "box": "\ue7b8", "receipt": "\ue8a5",
          "shield": "\ue730", "settings": "\ue713", "store": "\ue719", "back": "\ue72b",
          "next": "\ue72a", "search": "\ue721", "plus": "\ue710", "minus": "\ue738",
          "close": "\ue711", "delete": "\ue74d", "edit": "\ue70f", "print": "\ue749",
          "save": "\ue74e", "export": "\ue898", "eye": "\ue890", "clock": "\ue823",
          "calendar": "\ue787", "user": "\ue77b", "check": "\ue73e", "copy": "\ue8c8",
          "chart": "\ue9d9", "money": "\ue8c7", "tag": "\ue8ec", "info": "\ue946",
          "scan": "\ue722", "link": "\ue71b", "database": "\ue753",
          "image": "\ue91b", "lock": "\ue72e", "mail": "\ue715"}


@lru_cache(maxsize=160)
def icon(name, color=T.MUTED, size=20):
    canvas = Image.new("RGBA", (size * 3, size * 3))
    draw = ImageDraw.Draw(canvas)
    path = Path("C:/Windows/Fonts/segmdl2.ttf")
    if path.exists():
        face = ImageFont.truetype(str(path), size * 3 - 5)
        draw.text((size * 1.5, size * 1.5), GLYPHS.get(name, GLYPHS["box"]),
                  font=face, fill=color, anchor="mm")
    else:
        draw.rectangle((9, 9, size * 3 - 9, size * 3 - 9), outline=color, width=3)
    return ctk.CTkImage(canvas, size=(size, size))


@lru_cache(maxsize=64)
def product_image(key, size=76):
    """Decode bundled files once per size; there is no URL/network fallback."""
    if key in LOCAL_IMAGES:
        return ctk.CTkImage(LOCAL_IMAGES[key], size=(size, size))
    path = ASSETS / "products" / f"{key}.jpg"
    if path.exists():
        with Image.open(path) as source:
            source = ImageOps.exif_transpose(source).convert("RGBA")
            fitted = ImageOps.contain(source, (size * 2, size * 2), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (size * 2, size * 2), "white")
            canvas.paste(fitted, ((size * 2 - fitted.width) // 2, (size * 2 - fitted.height) // 2), fitted)
        return ctk.CTkImage(canvas, size=(size, size))
    return icon("box", T.MUTED, size)


def label(parent, text="", size=14, bold=False, color=T.INK, **kwargs):
    return ctk.CTkLabel(parent, text=text, font=T.font(size, bold), text_color=color,
                        anchor=kwargs.pop("anchor", "w"), **kwargs)


def panel(parent, **kwargs):
    return ctk.CTkFrame(parent, fg_color=T.WHITE, corner_radius=8, **kwargs)


def button(parent, text, command, symbol=None, kind="soft", width=120, **kwargs):
    colors = {"primary": (T.BLUE, T.WHITE, "#0860DC"),
              "soft": (T.BLUE_LIGHT, T.BLUE, "#DCEAFF"),
              "neutral": (T.BG, T.MUTED, T.LINE),
              "danger": (T.RED_LIGHT, T.RED, "#FFE0E5"),
              "green": (T.GREEN_LIGHT, T.GREEN, "#CAF0D9")}
    bg, fg, hover = colors[kind]
    widget = ctk.CTkButton(parent, text=text, command=command, font=T.font(13),
                           fg_color=bg, text_color=fg, hover_color=hover,
                           corner_radius=kwargs.pop("corner_radius", 7),
                           height=kwargs.pop("height", 34), width=width,
                           image=icon(symbol, fg, kwargs.pop("icon_size", 17)) if symbol else None,
                           compound="left", **kwargs)
    return widget


def icon_button(parent, symbol, command, hint, kind="soft", size=24):
    # CTk's default border spacing can enlarge an icon-only button beyond its
    # requested size. Explicit spacing keeps the small X/quantity controls fixed.
    widget = button(parent, "", command, symbol, kind=kind, width=size,
                    height=size, icon_size=12 if symbol == "close" else 14,
                    border_spacing=0, corner_radius=4)
    Tooltip(widget, hint)
    return widget


def badge(parent, text, tone="green"):
    colors = {"green": (T.GREEN_LIGHT, T.GREEN), "blue": (T.BLUE_LIGHT, T.BLUE),
              "red": (T.RED_LIGHT, T.RED), "amber": (T.AMBER_LIGHT, T.AMBER),
              "purple": (T.PURPLE_LIGHT, T.PURPLE)}
    bg, fg = colors[tone]
    return label(parent, text, size=12, color=fg, fg_color=bg, corner_radius=6,
                 height=27, padx=9)


def entry(parent, placeholder, variable=None, width=240):
    widget = ctk.CTkEntry(parent, placeholder_text=placeholder,
                         width=width, height=40, font=T.font(13), corner_radius=7,
                         fg_color=T.WHITE, border_color=T.LINE, text_color=T.INK)
    if variable is not None:
        # CTk hides placeholders when textvariable is attached. Synchronize instead.
        widget.bind("<KeyRelease>", lambda event: variable.set(widget.get()), add="+")
        def sync(*_):
            if widget.winfo_exists() and widget.get() != variable.get():
                widget.delete(0, "end")
                widget.insert(0, variable.get())
        trace = variable.trace_add("write", sync)
        widget.bind("<Destroy>", lambda event: variable.trace_remove("write", trace), add="+")
    return widget


def select(parent, values, command=None, width=170):
    return ctk.CTkOptionMenu(parent, values=values, command=command, width=width,
                            height=40, font=T.font(13), fg_color=T.WHITE,
                            text_color=T.INK, button_color=T.WHITE, button_hover_color=T.LINE,
                            dropdown_fg_color=T.WHITE, dropdown_text_color=T.INK,
                            dropdown_hover_color=T.BLUE_LIGHT, corner_radius=7,
                            dynamic_resizing=False)


class Page(ctk.CTkScrollableFrame):
    """Long report/detail pages scroll as one document; POS uses FixedPage."""
    def __init__(self, app):
        super().__init__(app.content, fg_color=T.BG, corner_radius=0,
                         scrollbar_button_color="#CFD9E7")
        self.app = app
        self.store = app.store
        self.grid_columnconfigure(0, weight=1)
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=0, sticky="nsew", padx=22, pady=20)
        self.body.grid_columnconfigure(0, weight=1)

    def heading(self, title, subtitle="", back=None):
        frame = ctk.CTkFrame(self.body, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 20))
        if back:
            button(frame, back[0], back[1], "back", kind="neutral", width=170).pack(anchor="w", pady=(0, 8))
        text = ctk.CTkFrame(frame, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        label(text, title, 30, True).pack(anchor="w")
        if subtitle:
            label(text, subtitle, 15, color=T.MUTED).pack(anchor="w", pady=(2, 0))
        return frame


class FixedPage(ctk.CTkFrame):
    """A viewport-sized page whose child panels own their scrolling."""
    heading = Page.heading

    def __init__(self, app):
        super().__init__(app.content, fg_color=T.BG, corner_radius=0)
        self.app, self.store = app, app.store
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=0, sticky="nsew", padx=20, pady=18)


class ScrollArea(ctk.CTkScrollableFrame):
    """An independent scroll pane; its viewport width never follows child sizes."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=kwargs.pop("fg_color", T.WHITE),
                         corner_radius=0, scrollbar_button_color="#CCD8E7", **kwargs)
        self.grid_columnconfigure(0, weight=1)


class Metric(ctk.CTkFrame):
    def __init__(self, parent, title, value, symbol, tone="blue", detail=""):
        super().__init__(parent, fg_color=T.WHITE, corner_radius=8, height=104)
        colors = {"blue": (T.BLUE_LIGHT, T.BLUE), "green": (T.GREEN_LIGHT, T.GREEN),
                  "amber": (T.AMBER_LIGHT, T.AMBER), "red": (T.RED_LIGHT, T.RED),
                  "purple": (T.PURPLE_LIGHT, T.PURPLE)}
        bg, fg = colors[tone]
        label(self, "", image=icon(symbol, fg, 26), width=50, height=50,
              fg_color=bg, corner_radius=8).pack(side="left", padx=(16, 12), pady=20)
        texts = ctk.CTkFrame(self, fg_color="transparent")
        texts.pack(side="left", fill="x", expand=True, padx=(0, 12))
        label(texts, title, 12, color=T.MUTED).pack(anchor="w")
        label(texts, value, 25, True).pack(anchor="w")
        if detail:
            label(texts, detail, 11, color=fg).pack(anchor="w")


class Table(ctk.CTkFrame):
    """Column weights keep rows aligned while the containing window resizes."""
    def __init__(self, parent, columns, weights=None):
        super().__init__(parent, fg_color=T.WHITE, corner_radius=0)
        self.columns = columns
        self.weights = weights or [1] * len(columns)
        header = self.row_frame(T.BG)
        for i, name in enumerate(columns):
            label(header, name, 12, color=T.MUTED).grid(row=0, column=i, sticky="w", padx=10, pady=11)

    def row_frame(self, color=T.WHITE):
        frame = ctk.CTkFrame(self, fg_color=color, corner_radius=0)
        frame.pack(fill="x")
        for i, weight in enumerate(self.weights):
            frame.grid_columnconfigure(i, weight=weight, uniform="columns")
        return frame

    def add(self, values, command=None):
        frame = self.row_frame()
        for i, value in enumerate(values):
            if callable(value):
                widget = value(frame)
            else:
                widget = label(frame, str(value), 12)
            widget.grid(row=0, column=i, sticky="w", padx=10, pady=9)
            if command and not isinstance(widget, ctk.CTkButton):
                widget.configure(cursor="hand2")
                widget.bind("<Button-1>", lambda event, fn=command: fn())
        if command:
            frame.bind("<Button-1>", lambda event: command())
        ctk.CTkFrame(self, fg_color=T.LINE, height=1, corner_radius=0).pack(fill="x")
        return frame


def key_values(parent, pairs):
    for key, value in pairs:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=1)
        label(row, key, 13, color=T.MUTED).pack(side="left", padx=4, pady=7)
        label(row, str(value), 13).pack(side="right", padx=4, pady=7)
        ctk.CTkFrame(parent, fg_color=T.LINE, height=1, corner_radius=0).pack(fill="x")


class Chart(tk.Canvas):
    def __init__(self, parent, values, labels, bars=False, height=200):
        super().__init__(parent, background=T.WHITE, highlightthickness=0, height=height)
        self.values, self.labels, self.bars = values, labels, bars
        self.bind("<Configure>", self.draw)

    def draw(self, event=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        left, top, right, bottom = 44, 15, w - 16, h - 30
        raw_step = max(max(self.values), 1) / 4
        magnitude = 10 ** math.floor(math.log10(raw_step))
        step_size = next(n for n in (1, 2, 2.5, 5, 10) if n >= raw_step / magnitude) * magnitude
        if self.bars:
            step_size = max(1, math.ceil(step_size))
        ceiling = step_size * 4
        for i in range(5):
            y = bottom - (bottom - top) * i / 4
            self.create_line(left, y, right, y, fill=T.LINE)
            number = ceiling * i / 4
            tick = f"{number / 1000:g}K" if ceiling > 1000 and number else f"{number:g}"
            self.create_text(left - 9, y, text=tick, anchor="e", fill=T.MUTED, font=T.font(10))
        step = (right - left) / max(len(self.values) - (0 if self.bars else 1), 1)
        points = []
        for i, value in enumerate(self.values):
            x = left + step * (i + (0.5 if self.bars else 0))
            y = bottom - value / ceiling * (bottom - top)
            points.extend((x, y))
            if self.bars:
                self.create_rectangle(x - step * .25, y, x + step * .25, bottom, fill="#82B4FF", outline="")
            self.create_text(x, bottom + 19, text=self.labels[i], fill=T.MUTED, font=T.font(10))
        if not self.bars:
            self.create_polygon([left, bottom] + points + [right, bottom], fill="#E6F0FF", outline="")
            self.create_line(*points, fill=T.BLUE, width=2.5)
            for x, y in zip(points[::2], points[1::2]):
                self.create_oval(x-3, y-3, x+3, y+3, fill=T.BLUE, outline=T.BLUE)


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.window, self.job = widget, text, None, None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<Button-1>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def schedule(self, event):
        self.job = self.widget.after(500, self.show)

    def show(self):
        self.job = None
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.geometry(f"+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty()+self.widget.winfo_height()+5}")
        tk.Label(self.window, text=self.text, bg=T.INK, fg="white", padx=8, pady=5, font=T.font(11)).pack()

    def hide(self, event=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.window:
            self.window.destroy()
            self.window = None
