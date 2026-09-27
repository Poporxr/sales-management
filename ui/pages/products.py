"""Products table with persistent rows, filters, and the batch-two forms."""

import math
import tkinter as tk
import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import (FixedPage, ScrollArea, Table, label, button, entry,
                                   select, badge, icon_button, product_image)
from ui.components.product_dialogs import ProductDialog, StockDialog, delete_product, CATEGORIES

WEIGHTS = [1, 6, 3, 2, 1, 3, 3]


class ProductRow(ctk.CTkFrame):
    def __init__(self, parent, page, product):
        super().__init__(parent, fg_color=T.WHITE, corner_radius=0)
        self.product = product
        for column, weight in enumerate(WEIGHTS):
            self.grid_columnconfigure(column, weight=weight, uniform="columns")
        self.number = label(self, "", 12, color=T.MUTED)
        self.number.grid(row=0, column=0, padx=8, sticky="w")
        identity = ctk.CTkFrame(self, fg_color="transparent")
        identity.grid(row=0, column=1, sticky="w", padx=8, pady=8)
        self.photo = label(identity, "", width=38)
        self.photo.pack(side="left", padx=(0, 10))
        self.name = label(identity, "", 12, True, wraplength=175, justify="left", cursor="hand2")
        self.name.pack(side="left")
        self.name.bind("<Button-1>", lambda event: page.app.navigate("product", product_id=product["id"]))
        self.category = label(self, "", 12, color=T.MUTED)
        self.category.grid(row=0, column=2, padx=8, sticky="w")
        self.price = label(self, "", 12, True)
        self.price.grid(row=0, column=3, padx=8, sticky="w")
        self.stock = label(self, "", 12)
        self.stock.grid(row=0, column=4, padx=8, sticky="w")
        self.status = badge(self, "")
        self.status.grid(row=0, column=5, padx=8, sticky="w")
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=0, column=6, padx=8, sticky="w")
        icon_button(actions, "edit", lambda: ProductDialog(page.app, product["id"]), "Edit product", size=22).pack(side="left", padx=2)
        icon_button(actions, "box", lambda: StockDialog(page.app, product["id"]), "Adjust stock", "green", 22).pack(side="left", padx=2)
        icon_button(actions, "delete", lambda: delete_product(page.app, product["id"]), "Delete product", "danger", 22).pack(side="left", padx=2)
        ctk.CTkFrame(self, height=1, corner_radius=0, fg_color=T.LINE).grid(row=1, column=0, columnspan=7, sticky="ew")
        self.refresh()

    def refresh(self):
        p = self.product
        self.name.configure(text=p["name"])
        self.photo.configure(image=product_image(p["image"], 38))
        self.category.configure(text=p["category"])
        self.price.configure(text=T.money(p["price"]))
        self.stock.configure(text=str(p["stock"]))
        from services.mock_store import MockStore
        status = MockStore.stock_status(p)
        self.status.configure(text=status, text_color=T.GREEN if status == "In Stock" else T.RED,
                              fg_color=T.GREEN_LIGHT if status == "In Stock" else T.RED_LIGHT)


class ProductsPage(FixedPage):
    def __init__(self, app):
        super().__init__(app)
        self.rows, self.filtered = {}, []
        self.product_revision, self.page_number = -1, 1
        self.query = tk.StringVar()
        heading = self.heading("Products", "Manage your store products.")
        button(heading, "Add Product", lambda: ProductDialog(app), "plus", kind="primary", width=140).pack(side="right")
        filters = ctk.CTkFrame(self.body, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 14))
        self.search = entry(filters, "Search product name or barcode...", self.query)
        self.search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.category = select(filters, ["All Categories"] + CATEGORIES, self.filter_changed, width=160)
        self.category.pack(side="left", padx=(0, 10))
        self.status = select(filters, ["All Statuses", "In Stock", "Low Stock", "Out of Stock"], self.filter_changed, width=140)
        self.status.pack(side="left", padx=(0, 10))
        self.sort = select(filters, ["Newest First", "Name", "Stock: Low to High"], self.filter_changed, width=150)
        self.sort.pack(side="left")
        footer = ctk.CTkFrame(self.body, fg_color="transparent")
        footer.pack(side="bottom", fill="x", pady=(14, 0))
        self.prev = icon_button(footer, "back", lambda: self.move(-1), "Previous page")
        self.prev.pack(side="left")
        self.page_label = label(footer, "", width=100, anchor="center")
        self.page_label.pack(side="left")
        self.next = icon_button(footer, "next", lambda: self.move(1), "Next page")
        self.next.pack(side="left")
        self.count = label(footer, "", 13, color=T.MUTED)
        self.count.pack(side="right")
        self.scroll = ScrollArea(self.body)
        self.scroll.pack(fill="both", expand=True)
        self.table = Table(self.scroll, ["#", "Product", "Category", "Price", "Stock", "Status", "Actions"], WEIGHTS)
        self.table.pack(fill="x")
        self.empty = label(self.scroll, "No products found", 16, color=T.MUTED)
        self.query.trace_add("write", self.filter_changed)
        self.refresh()

    def refresh(self):
        if self.product_revision == self.store.product_revision:
            return
        ids = {p["id"] for p in self.store.products}
        for pid in set(self.rows) - ids:
            self.rows.pop(pid).destroy()
        for product in self.store.products:
            pid = product["id"]
            if pid not in self.rows:
                self.rows[pid] = ProductRow(self.table, self, product)
            else:
                self.rows[pid].refresh()
        self.product_revision = self.store.product_revision
        self.filter_changed()

    def filter_changed(self, *_):
        query = self.query.get().strip().lower()
        self.filtered = [p for p in self.store.products if
                         (query in p["name"].lower() or query in p["barcode"]) and
                         (self.category.get() == "All Categories" or p["category"] == self.category.get()) and
                         (self.status.get() == "All Statuses" or self.store.stock_status(p) == self.status.get())]
        key = {"Newest First": "id", "Name": "name", "Stock: Low to High": "stock"}[self.sort.get()]
        self.filtered.sort(key=lambda p: p[key], reverse=key == "id")
        self.page_number = 1
        self.render_rows()

    def render_rows(self):
        # Repack existing rows in the selected order; no images are reloaded.
        for row in self.rows.values():
            row.pack_forget()
        start = (self.page_number - 1) * 10
        for index, product in enumerate(self.filtered[start:start+10], start+1):
            row = self.rows[product["id"]]
            row.number.configure(text=str(index))
            row.pack(fill="x")
        pages = max(1, math.ceil(len(self.filtered) / 10))
        self.page_label.configure(text=f"{self.page_number} / {pages}")
        self.prev.configure(state="normal" if self.page_number > 1 else "disabled")
        self.next.configure(state="normal" if self.page_number < pages else "disabled")
        self.count.configure(text=f"Showing {start+1 if self.filtered else 0}-{min(start+10,len(self.filtered))} of {len(self.filtered)} products")
        if self.filtered:
            self.empty.pack_forget()
        else:
            self.empty.pack(pady=50)

    def move(self, delta):
        self.page_number = max(1, min(max(1, math.ceil(len(self.filtered)/10)), self.page_number + delta))
        self.render_rows()
        self.scroll._parent_canvas.yview_moveto(0)
