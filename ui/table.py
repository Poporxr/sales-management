"""A simple styled table used by the Sales History and Audit Log pages.

Built on tkinter's ttk.Treeview: real column headers, row selection,
and a scrollbar, with the app's colors applied through ttk.Style.
Columns is a list of (key, heading, width) tuples.
"""

import tkinter as tk
from tkinter import ttk

from ui import theme as T


def make_table(parent, columns):
    """Create the table and return it. Insert rows with
    table.insert("", "end", values=(...)). Read the selected row's
    values with table.item(table.selection()[0], "values")."""
    style = ttk.Style()
    # Plain (non-themed) style names so CustomTkinter's theme never
    # fights us for these widgets.
    style.configure("Shop.Treeview",
                    font=(T.FONT, 12),
                    rowheight=34,
                    background=T.WHITE,
                    fieldbackground=T.WHITE,
                    foreground=T.INK,
                    borderwidth=0,
                    padding=(8, 0))
    style.configure("Shop.Treeview.Heading",
                    font=(T.FONT, 12, "bold"),
                    background=T.LINE,
                    foreground=T.INK,
                    borderwidth=0,
                    padding=(8, 10))
    style.map("Shop.Treeview",
              background=[("selected", T.ACCENT)],
              foreground=[("selected", T.WHITE)])

    table = ttk.Treeview(parent, columns=[c[0] for c in columns],
                         show="headings", style="Shop.Treeview",
                         selectmode="browse")
    for key, heading, width in columns:
        # Headings centered over their columns; cell text stays
        # left-aligned for readability. minwidth keeps narrow columns
        # from collapsing when the window is small.
        table.heading(key, text=heading, anchor="center")
        table.column(key, width=width, minwidth=width // 2,
                     anchor="w", stretch=True)

    scrollbar = ttk.Scrollbar(parent, orient="vertical",
                              command=table.yview)
    table.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    table.pack(side="left", fill="both", expand=True)
    return table


def clear_table(table):
    """Remove every row, so the page can refill it."""
    for row_id in table.get_children():
        table.delete(row_id)


# The date filter choices shared by both pages. The key is what the
# database filter functions expect; the label is what the user sees.
DATE_FILTERS = [
    ("all", "All dates"),
    ("today", "Today"),
    ("yesterday", "Yesterday"),
    ("week", "Last 7 days"),
    ("month", "Last 30 days"),
]
