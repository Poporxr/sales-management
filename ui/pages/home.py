"""Home dashboard: today's numbers, warnings, and recent sales.

Everything on this screen is computed fresh from the database each
time the page opens, so it can never show stale numbers.
"""

import customtkinter as ctk

import database
from ui import theme as T
from ui.widgets import label, card


class HomePage(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.content, fg_color="transparent")
        self.app = app

        label(self, "Home", 24, True).pack(anchor="w", pady=(0, 4))
        label(self, app.config["store_name"] + "  |  " + app.config["address"],
              13, color=T.MUTED).pack(anchor="w", pady=(0, 18))

        summary = database.today_summary()
        stats = [
            ("Sales today", str(summary["count"])),
            ("Revenue today", T.money(summary["revenue"])),
            ("Products", str(database.count_products())),
            ("Out of stock", str(len(database.out_of_stock_products()))),
        ]
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, 18))
        for title, value in stats:
            c = card(row)
            c.pack(side="left", fill="x", expand=True, padx=(0, 12))
            label(c, title, 13, color=T.MUTED).pack(anchor="w", padx=18, pady=(14, 0))
            label(c, value, 24, True).pack(anchor="w", padx=18, pady=(2, 14))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True)

        # Out-of-stock warnings.
        left = card(bottom)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        label(left, "Out of stock", 16, True).pack(anchor="w", padx=18, pady=(14, 8))
        empty = database.out_of_stock_products()
        if not empty:
            label(left, "Everything is in stock.", 13,
                  color=T.MUTED).pack(anchor="w", padx=18, pady=(0, 14))
        for p in empty:
            label(left, "%s  (%s)" % (p["name"], p["barcode"]), 13).pack(
                anchor="w", padx=18, pady=2)

        # Recent sales.
        right = card(bottom)
        right.pack(side="left", fill="both", expand=True)
        label(right, "Recent sales", 16, True).pack(anchor="w", padx=18, pady=(14, 8))
        for sale in database.list_sales(limit=8):
            label(right, "#%06d  |  %s  |  %s" % (
                sale["id"], sale["date"][5:16], T.money(sale["total"])),
                13).pack(anchor="w", padx=18, pady=2)
