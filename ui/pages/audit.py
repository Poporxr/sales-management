"""Audit Log: who did what and when, in a table.

Append-only and deliberately plain: newest first, with date, action
type, and search filters. Entries are written at critical points only
(product added, edited, deleted, stock adjusted, sale completed), so
a supervisor can trace every sensitive change in one place.
"""

import tkinter as tk

import customtkinter as ctk

import database
from ui import theme as T
from ui.widgets import label, entry, dropdown
from ui.table import make_table, clear_table, DATE_FILTERS


class AuditPage(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.content, fg_color="transparent")

        label(self, "Audit Log", 24, True).pack(anchor="w", pady=(0, 4))
        label(self, "Critical actions only. Entries cannot be edited.",
              13, color=T.MUTED).pack(anchor="w", pady=(0, 12))

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 10))
        self.search_var = tk.StringVar()
        search = entry(filters, "Search user, action, details...", width=260)
        search.pack(side="left", padx=(0, 8))
        search.configure(textvariable=self.search_var)
        self.search_var.trace_add("write", lambda *_: self.render())

        label(filters, "Date:", 13).pack(side="left", padx=(0, 6))
        self.period = dropdown(filters,
                               [text for _, text in DATE_FILTERS],
                               command=lambda _: self.render(), width=140)
        self.period.pack(side="left", padx=(0, 8))

        label(filters, "Action:", 13).pack(side="left", padx=(0, 6))
        self.action_filter = dropdown(
            filters, ["All actions"] + database.list_audit_actions(),
            command=lambda _: self.render(), width=160)
        self.action_filter.pack(side="left")

        table_frame = ctk.CTkFrame(self, fg_color=T.WHITE, corner_radius=10)
        table_frame.pack(fill="both", expand=True)
        self.table = make_table(table_frame, [
            ("date", "Date", 150),
            ("user", "User", 110),
            ("action", "Action", 140),
            ("details", "Details", 400),
        ])
        self.render()

    def current_period(self):
        """Translate the dropdown's label back to the database filter key."""
        chosen = self.period.get()
        for key, text in DATE_FILTERS:
            if text == chosen:
                return key
        return "all"

    def current_action(self):
        """The chosen action type, or 'all' when nothing is picked."""
        chosen = self.action_filter.get()
        return "all" if chosen == "All actions" else chosen

    def render(self):
        clear_table(self.table)
        entries = database.list_audit_filtered(
            period=self.current_period(),
            action=self.current_action(),
            query=self.search_var.get())
        for e in entries:
            self.table.insert("", "end", values=(
                e["date"], e["user"], e["action"], e["details"] or ""))
