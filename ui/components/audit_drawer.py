"""A non-navigating audit inspector; closing preserves the table and filters."""

import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import label, icon_button, button, ScrollArea, key_values, Table, icon


class AuditDrawer(ctk.CTkFrame):
    def __init__(self, app, log_id):
        super().__init__(app.content, width=465, fg_color=T.WHITE, corner_radius=0,
                         border_width=1, border_color=T.LINE)
        self.app = app
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        log = next(row for row in app.store.logs if row["id"] == log_id)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        label(header, "Log Details", 21, True, image=icon("receipt", T.BLUE, 22), compound="left").pack(side="left")
        icon_button(header, "close", app.close_drawer, "Close log details", "neutral", 22).pack(side="right")
        body = ScrollArea(self)
        body.grid(row=1, column=0, sticky="nsew", padx=20)
        label(body, "Overview", 15, True).pack(anchor="w", pady=(0, 10))
        label(body, log["action"], 17, True, T.GREEN, fg_color=T.GREEN_LIGHT,
              corner_radius=6, padx=12, height=48).pack(fill="x")
        label(body, log["details"], 12, color=T.MUTED, wraplength=385, justify="left").pack(anchor="w", pady=10)
        key_values(body, [("Date & Time", log["date"].strftime("%d %b %Y, %I:%M %p")),
                          ("User", log["user"]), ("IP/Device", log["device"]),
                          ("Reference", log["sale_id"] or log["id"])])
        sale = app.store.sale(log["sale_id"]) if log["sale_id"] else None
        if sale:
            label(body, "Sale Details", 15, True).pack(anchor="w", pady=(20, 8))
            key_values(body, [("Total Items", len(sale["items"])), ("Total Amount", T.money(sale["total"])),
                              ("Payment Method", sale["payment"]), ("Amount Received", T.money(sale["paid"])),
                              ("Change", T.money(sale["paid"] - sale["total"]))])
            label(body, "Items in this Sale", 15, True).pack(anchor="w", pady=(20, 8))
            table = Table(body, ["Product", "Qty", "Price", "Total"], [4, 1, 2, 2])
            table.pack(fill="x")
            for item in sale["items"]:
                table.add([lambda p, item=item: label(p, item["name"], 11, wraplength=130, justify="left"),
                           item["quantity"], T.money(item["price"]), T.money(item["price"] * item["quantity"])])
        else:
            # Product actions carry snapshots; only changed fields are shown.
            label(body, "Changes", 15, True).pack(anchor="w", pady=(20, 8))
            before, after = log.get("before") or {}, log.get("after") or {}
            changes = []
            for key in ("name", "barcode", "category", "price", "cost", "stock", "minimum"):
                old, new = before.get(key, "-"), after.get(key, "-")
                if old != new:
                    changes.append((key.title(), f"{old}  >  {new}"))
            if changes:
                key_values(body, changes)
            else:
                label(body, "No field snapshot in this sample.", 12, color=T.MUTED).pack(anchor="w")
            if log["notes"]:
                label(body, "Notes", 15, True).pack(anchor="w", pady=(20, 8))
                label(body, log["notes"], 12, color=T.MUTED, wraplength=380, justify="left").pack(anchor="w")
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=18)
        if sale:
            button(footer, "View Receipt", lambda: app.navigate("sale", sale_id=sale["id"]), "receipt", width=135).pack(side="left")
        else:
            button(footer, "Full Details", lambda: app.navigate("log", log_id=log_id), "next", width=135).pack(side="left")
        button(footer, "Close", app.close_drawer, kind="primary", width=100).pack(side="right")
