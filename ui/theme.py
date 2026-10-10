"""Shared colors, fonts, and money formatting.

One place for the look of the app: if the owner wants a different
accent color later, it changes here and everywhere follows.
"""

BG = "#F3F6FB"        # app background
WHITE = "#FFFFFF"     # cards and panels
INK = "#10213B"       # main text
MUTED = "#587095"     # secondary text
LINE = "#E6EDF6"      # borders
ACCENT = "#1673FF"    # primary buttons and highlights
ACCENT_DARK = "#0F5BCC"
NAV = "#122536"       # sidebar
NAV_ACTIVE = "#1E3A5C"
NAV_TEXT = "#BCD0E4"
GREEN = "#0A7A3D"
RED = "#D63A47"
AMBER = "#B77A08"

FONT = "Segoe UI"


def font(size=14, bold=False):
    """CustomTkinter wants fonts as a (name, size, weight) tuple."""
    return (FONT, size, "bold" if bold else "normal")


def money(amount):
    """Naira formatting: whole amounts stay compact, kobo shows when needed."""
    amount = round(float(amount), 2)
    if amount == int(amount):
        return "\u20a6{:,.0f}".format(amount)
    return "\u20a6{:,.2f}".format(amount)
