"""Sales History: every completed sale in a table, newest first.

Date filter plus a search box narrow the rows. Double-click a row
(or select it and press Open) for the detail dialog: the frozen item
snapshots, the totals, and a Reprint receipt button that regenerates
the PDF from the stored rows and opens it.
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import database
import receipt
from ui import theme as T
from ui.widgets import label, button, entry, dropdown
from ui.table import make_table, clear_table, DATE_FILTERS


class HistoryPage(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.content, fg_color="transparent")
        self.app = app
        # sale id -> full sale dict, so a clicked row can open its dialog
        self.sale_ids = []

        label(self, "Sales History", 24, True).pack(anchor="w", pady=(0, 12))

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 10))
        self.search_var = tk.StringVar()
        search = entry(filters, "Search receipt number or cashier...", width=300)
        search.pack(side="left", padx=(0, 8))
        search.configure(textvariable=self.search_var)
        self.search_var.trace_add("write", lambda *_: self.render())
        self.period = dropdown(filters,
                               [text for _, text in DATE_FILTERS],
                               command=lambda _: self.render(), width=150)
        self.period.pack(side="left", padx=(0, 8))
        button(filters, "Open selected", self.open_selected,
               kind="secondary", width=140).pack(side="left")

        table_frame = ctk.CTkFrame(self, fg_color=T.WHITE, corner_radius=10)
        table_frame.pack(fill="both", expand=True)
        self.table = make_table(table_frame, [
            ("receipt", "Receipt", 90),
            ("date", "Date", 150),
            ("cashier", "Cashier", 110),
            ("items", "Items", 60),
            ("payment", "Payment", 90),
            ("total", "Total", 110),
        ])
        self.table.bind("<Double-1>", lambda e: self.open_selected())
        self.render()

    def current_period(self):
        """Translate the dropdown's label back to the database filter key."""
        chosen = self.period.get()
        for key, text in DATE_FILTERS:
            if text == chosen:
                return key
        return "all"

    def render(self):
        clear_table(self.table)
        self.sale_ids = []
        query = self.search_var.get().strip().lower()
        sales = database.list_sales_filtered(self.current_period())
        if query:
            sales = [s for s in sales
                     if query in str(s["id"]) or query in s["cashier"].lower()
                     or query in (s["customer_name"] or "").lower()]
        for sale in sales:
            full = database.get_sale(sale["id"])  # items for the count
            self.table.insert("", "end", values=(
                "#%06d" % sale["id"],
                sale["date"],
                sale["cashier"],
                len(full["items"]),
                sale["payment"],
                T.money(sale["total"]),
            ))
            self.sale_ids.append(sale["id"])

    def open_selected(self):
        """Open the detail dialog for the highlighted row."""
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("No sale selected",
                                "Click a row first, then open it.")
            return
        index = self.table.index(selection[0])
        SaleDialog(self, self.sale_ids[index])

    def reprint(self, sale_id):
        """Regenerate the PDF from the stored sale rows and open it."""
        try:
            path = receipt.generate_receipt(sale_id, self.app.config)
        except Exception as e:
            messagebox.showerror("Reprint failed",
                                 "Could not build the receipt:\n%s" % e)
            return
        if not receipt.open_file(path):
            messagebox.showwarning(
                "No viewer found",
                "The receipt was saved to:\n%s\n\nOpen it manually to print."
                % path)


class SaleDialog(ctk.CTkToplevel):
    """One sale's detail: items, totals, payment, and reprint."""

    def __init__(self, page, sale_id):
        super().__init__(page)
        self.page = page
        sale = database.get_sale(sale_id)  # reload with items attached
        self.title("Receipt #%06d" % sale["id"])
        self.geometry("420x520")
        self.transient(page)
        self.grab_set()

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=20)

        label(body, "Receipt #%06d" % sale["id"], 18, True).pack(anchor="w")
        label(body, "%s  |  Cashier: %s" % (sale["date"], sale["cashier"]),
              12, color=T.MUTED).pack(anchor="w", pady=(0, 4))
        if sale["customer_name"]:
            label(body, "Customer: %s" % sale["customer_name"], 12,
                  color=T.MUTED).pack(anchor="w", pady=(0, 8))

        for item in sale["items"]:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=3)
            label(row, "%s  x%d" % (item["name"], item["quantity"]),
                  13).pack(side="left")
            label(row, T.money(item["price"] * item["quantity"]),
                  13, True).pack(side="right")

        label(body, "", 6).pack()  # spacer
        label(body, "Total: " + T.money(sale["total"]), 16, True).pack(anchor="e")
        label(body, "Paid (%s): %s" % (sale["payment"], T.money(sale["paid"])),
              13, color=T.MUTED).pack(anchor="e")
        if sale["payment"] == "Cash":
            label(body, "Change: " + T.money(sale["change"]), 13,
                  color=T.MUTED).pack(anchor="e")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 20))
        button(footer, "Reprint receipt",
               lambda: page.reprint(sale["id"])).pack(fill="x", pady=(0, 8))
        button(footer, "Close", self.destroy, kind="secondary").pack(fill="x")
