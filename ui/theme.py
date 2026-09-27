"""Shared desktop palette and typography."""

BG = "#F3F6FB"
WHITE = "#FFFFFF"
INK = "#10213B"
MUTED = "#587095"
LINE = "#E6EDF6"
BLUE = "#1673FF"
BLUE_LIGHT = "#EAF2FF"
NAV = "#122536"
NAV_ACTIVE = "#193F68"
NAV_TEXT = "#BCD0E4"
GREEN = "#079447"
GREEN_LIGHT = "#E0F7E9"
RED = "#E74955"
RED_LIGHT = "#FFF0F2"
AMBER = "#B77A08"
AMBER_LIGHT = "#FFF6E1"
PURPLE = "#8150CC"
PURPLE_LIGHT = "#F2ECFF"
FONT = "Segoe UI"


def font(size=14, bold=False):
    return (FONT, size, "bold" if bold else "normal")


def money(amount):
    return "\u20a6" + f"{amount:,.0f}"
