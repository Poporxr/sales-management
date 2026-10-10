"""Tiny widget helpers so pages stay readable.

Each helper is one obvious wrapper around a CustomTkinter widget
with the app's defaults baked in. Pages call these instead of
repeating the same styling arguments everywhere.
"""

import customtkinter as ctk

from ui import theme as T


def label(parent, text="", size=14, bold=False, color=T.INK, **kwargs):
    """A text label. Pass font=... to override the default typeface."""
    font = kwargs.pop("font", T.font(size, bold))
    return ctk.CTkLabel(parent, text=text, font=font,
                        text_color=color, **kwargs)


def button(parent, text, command, kind="primary", width=120, **kwargs):
    """A button. kind is primary (blue), secondary (light), or danger (red)."""
    colors = {
        "primary": (T.ACCENT, T.WHITE),
        "secondary": (T.LINE, T.INK),
        "danger": (T.RED, T.WHITE),
    }
    fg, text_color = colors[kind]
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=fg, text_color=text_color,
                         hover_color=T.ACCENT_DARK if kind == "primary" else fg,
                         font=T.font(14), width=width, height=36,
                         corner_radius=8, **kwargs)


def entry(parent, placeholder="", width=200, **kwargs):
    """A single-line text input."""
    return ctk.CTkEntry(parent, placeholder_text=placeholder, width=width,
                        height=36, font=T.font(14), **kwargs)


def card(parent, **kwargs):
    """A white rounded panel sitting on the gray background."""
    return ctk.CTkFrame(parent, fg_color=T.WHITE, corner_radius=10,
                        border_width=1, border_color=T.LINE, **kwargs)


def dropdown(parent, values, command=None, width=160, **kwargs):
    """A dropdown menu (CustomTkinter calls it an OptionMenu)."""
    return ctk.CTkOptionMenu(parent, values=values, command=command,
                             width=width, height=36, font=T.font(14),
                             fg_color=T.WHITE, text_color=T.INK,
                             button_color=T.ACCENT, **kwargs)
