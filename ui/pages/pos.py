"""Point of sale: persistent widgets and independent product/cart scrolling."""

import tkinter as tk
import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import (FixedPage, ScrollArea, label, panel, button,
                                   entry, select, badge, product_image, icon_button)
from ui.components.dialogs import CheckoutDialog, SaleCompletedDialog, confirm, edit_text

CATEGORIES = ["Beverages", "Snacks", "Groceries", "Household", "Personal Care", "Others"]


class ProductTile(ctk.CTkFrame):
    """Filtering and resizing move this tile rather than rebuilding it."""
    def __init__(self, parent, page, product):
        super().__init__(parent, fg_color=T.WHITE, border_width=1,
                         border_color=T.LINE, corner_radius=8, height=148)
        self.product = product
        self.grid_columnconfigure(1, weight=1)
        self.photo = label(self, "", cursor="hand2")
        self.photo.grid(row=0, column=0, rowspan=3, padx=(10, 8), pady=12)
        self.name = label(self, "", 12, True, wraplength=125, justify="left", cursor="hand2")
        self.name.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(12, 0))
        self.code = label(self, "", 10, color=T.MUTED)
        self.code.grid(row=1, column=1, sticky="w")
        self.price = label(self, "", 18, True)
        self.price.grid(row=2, column=1, sticky="w", pady=(0, 6))
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        self.stock = badge(bottom, "")
        self.stock.pack(side="left")
        self.add_button = icon_button(bottom, "plus", lambda: page.change_quantity(product["id"], 1), "Add to sale")
        self.add_button.pack(side="right")
        for widget in (self.photo, self.name):
            widget.bind("<Button-1>", lambda event: page.app.navigate("product", product_id=product["id"]))
        self.refresh()

    def refresh(self):
        p = self.product
        self.name.configure(text=p["name"])
        self.code.configure(text=p["barcode"])
        self.price.configure(text=T.money(p["price"]))
        self.photo.configure(image=product_image(p["image"], 56))
        low = p["stock"] <= p["minimum"]
        self.stock.configure(text=f"In stock: {p['stock']}", text_color=T.AMBER if low else T.GREEN,
                             fg_color=T.AMBER_LIGHT if low else T.GREEN_LIGHT)
        self.add_button.configure(state="normal" if p["stock"] else "disabled")


class CartRow(ctk.CTkFrame):
    """One row owns its labels, so changing quantity preserves focus and layout."""
    def __init__(self, parent, page, product_id):
        super().__init__(parent, fg_color=T.WHITE, corner_radius=0)
        self.page, self.product_id, self.last_value = page, product_id, None
        self.grid_columnconfigure(1, weight=1)
        self.photo = label(self, "", width=38)
        self.photo.grid(row=0, column=0, rowspan=3, padx=(0, 8), pady=8)
        self.name = label(self, "", 12, True, height=20, wraplength=165, justify="left")
        self.name.grid(row=0, column=1, sticky="w", pady=(8, 0))
        self.unit_price = label(self, "", 11, color=T.MUTED, height=18)
        self.unit_price.grid(row=1, column=1, sticky="w")
        self.remove_button = icon_button(self, "close", lambda: page.remove(product_id), "Remove item", "neutral", 20)
        self.remove_button.grid(row=0, column=2, sticky="e", padx=(5, 0))
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=1, sticky="w", pady=(4, 8))
        icon_button(controls, "minus", lambda: page.change_quantity(product_id, -1), "Decrease quantity", "neutral", 22).pack(side="left")
        self.quantity = label(controls, "", 12, True, width=28, height=22, anchor="center")
        self.quantity.pack(side="left")
        icon_button(controls, "plus", lambda: page.change_quantity(product_id, 1), "Increase quantity", "neutral", 22).pack(side="left")
        self.total = label(self, "", 13, True)
        self.total.grid(row=2, column=2, sticky="e", padx=(4, 0))
        ctk.CTkFrame(self, height=1, fg_color=T.LINE, corner_radius=0).grid(row=3, column=0, columnspan=3, sticky="ew")
        self.refresh()

    def refresh(self):
        p = self.page.store.product(self.product_id)
        qty = self.page.store.cart[self.product_id]
        value = (p["name"], p["price"], p["image"], qty)
        if value == self.last_value:
            return
        self.name.configure(text=p["name"])
        self.unit_price.configure(text=f"{T.money(p['price'])} each")
        self.photo.configure(image=product_image(p["image"], 36))
        self.quantity.configure(text=str(qty))
        self.total.configure(text=T.money(qty * p["price"]))
        self.last_value = value


class SalePage(FixedPage):
    def __init__(self, app):
        super().__init__(app)
        self.columns, self.pending_columns = 2, 2
        self.layout_job = None
        self.tiles, self.cart_rows = {}, {}
        self.product_revision = -1
        self.query = tk.StringVar()
        header = self.heading("New Sale", "Scan a barcode or select products for the current sale.")
        button(header, "Scan Barcode", self.focus_search, "scan", width=140).pack(side="right")

        # Constrain the workspace to the viewport. Each pane scrolls its own
        # content instead of making the whole page grow with every cart row.
        workspace = ctk.CTkFrame(self.body, fg_color="transparent")
        workspace.pack(fill="both", expand=True)
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_propagate(False)
        left = ctk.CTkFrame(workspace, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        filters = ctk.CTkFrame(left, fg_color="transparent")
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.search = entry(filters, "Search product name or barcode...", self.query)
        self.search.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search.bind("<Return>", self.scan)
        self.sort = select(filters, ["Sort: Name", "Price: Low to High", "Stock: Low to High"], lambda _: self.render_products(), width=150)
        self.sort.pack(side="right")
        categories = ctk.CTkFrame(left, fg_color="transparent")
        categories.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.category_select = select(categories, ["All Categories"] + CATEGORIES, lambda _: self.render_products())
        self.category_select.pack(side="left")
        self.count_label = label(categories, "", 12, color=T.MUTED)
        self.count_label.pack(side="right")
        self.products_frame = ScrollArea(left, fg_color=T.BG)
        self.products_frame.grid(row=2, column=0, sticky="nsew")
        self.products_frame._parent_canvas.bind("<Configure>", self.resize_grid, add="+")
        self.empty_products = label(self.products_frame, "No products found", 16, color=T.MUTED)

        # The cart header and payment footer stay fixed while only items scroll.
        self.cart_panel = panel(workspace, width=342)
        self.cart_panel.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        self.cart_panel.grid_propagate(False)
        self.cart_panel.grid_columnconfigure(0, weight=1)
        self.cart_panel.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(self.cart_panel, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.cart_title = label(top, "Current Sale", 16, True)
        self.cart_title.pack(side="left")
        icon_button(top, "delete", self.clear, "Clear cart", "danger").pack(side="right")
        icon_button(top, "edit", self.edit_note, "Sale note").pack(side="right", padx=5)
        self.cart_scroll = ScrollArea(self.cart_panel, height=100)
        self.cart_scroll.grid(row=1, column=0, sticky="nsew", padx=(12, 4))
        self.empty_cart = label(self.cart_scroll, "Your cart is empty", 15, color=T.MUTED)
        footer = ctk.CTkFrame(self.cart_panel, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 12))
        discount = ctk.CTkFrame(footer, fg_color="transparent")
        discount.pack(fill="x", pady=(0, 6))
        self.discount_entry = entry(discount, "Discount code", width=120)
        self.discount_entry.configure(height=30)
        self.discount_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        button(discount, "Apply", self.apply_discount, width=54, height=30).pack(side="right")
        self.totals = {}
        for name in ("Subtotal", "Discount", "Total"):
            row = ctk.CTkFrame(footer, fg_color=T.BLUE_LIGHT if name == "Total" else "transparent", corner_radius=6)
            row.pack(fill="x", pady=2)
            label(row, name, 18 if name == "Total" else 12, name == "Total", height=26).pack(side="left", padx=6)
            self.totals[name] = label(row, "", 21 if name == "Total" else 12, name == "Total", height=26)
            self.totals[name].pack(side="right", padx=6, pady=3)
        actions = ctk.CTkFrame(footer, fg_color="transparent")
        actions.pack(fill="x", pady=(8, 0))
        self.hold_button = button(actions, "Hold Sale", self.hold, "clock", width=95)
        self.hold_button.pack(side="left", padx=(0, 6))
        self.complete_button = button(actions, "Complete Sale", self.checkout, "money", kind="primary", width=170)
        self.complete_button.pack(side="right", fill="x", expand=True)
        self.query.trace_add("write", lambda *_: self.render_products())
        self.refresh()

    def refresh(self):
        # Product revisions change only after a product edit, never on a cart tap.
        if self.product_revision != self.store.product_revision:
            live_ids = {p["id"] for p in self.store.products}
            for pid in set(self.tiles) - live_ids:
                self.tiles.pop(pid).destroy()
            for product in self.store.products:
                pid = product["id"]
                if pid not in self.tiles:
                    self.tiles[pid] = ProductTile(self.products_frame, self, product)
                else:
                    self.tiles[pid].refresh()
            self.product_revision = self.store.product_revision
            self.render_products()
        self.render_cart()

    def resize_grid(self, event):
        columns = max(2, min(3, int(event.width / self._get_widget_scaling() // 235)))
        if columns != self.pending_columns:
            self.pending_columns = columns
            if self.layout_job:
                self.after_cancel(self.layout_job)
            self.layout_job = self.after(100, self.apply_columns)

    def apply_columns(self):
        self.layout_job = None
        self.columns = self.pending_columns
        self.render_products()

    def render_products(self):
        query, category = self.query.get().strip().lower(), self.category_select.get()
        products = [p for p in self.store.products if
                    (query in p["name"].lower() or query in p["barcode"]) and
                    (category == "All Categories" or category == p["category"])]
        key = {"Sort: Name": "name", "Price: Low to High": "price", "Stock: Low to High": "stock"}[self.sort.get()]
        products.sort(key=lambda p: p[key])
        visible = {p["id"] for p in products}
        for pid, tile in self.tiles.items():
            if pid not in visible:
                tile.grid_remove()
        for column in range(3):
            self.products_frame.grid_columnconfigure(column, weight=1 if column < self.columns else 0,
                                                       uniform="tiles" if column < self.columns else "")
        for index, product in enumerate(products):
            self.tiles[product["id"]].grid(row=index // self.columns, column=index % self.columns,
                                            sticky="nsew", padx=4, pady=4)
        self.count_label.configure(text=f"{len(products)} products")
        if products:
            self.empty_products.grid_remove()
        else:
            self.empty_products.grid(row=0, column=0, columnspan=self.columns, pady=50)

    def render_cart(self):
        # Reconcile by ID: remove missing rows, create new rows, and configure
        # changed values. The footer, inputs, and scroll canvas never rebuild.
        for pid in set(self.cart_rows) - set(self.store.cart):
            self.cart_rows.pop(pid).destroy()
        for pid in self.store.cart:
            if pid not in self.cart_rows:
                row = CartRow(self.cart_scroll, self, pid)
                row.pack(fill="x")
                self.cart_rows[pid] = row
            else:
                self.cart_rows[pid].refresh()
        if self.store.cart:
            self.empty_cart.pack_forget()
        else:
            self.empty_cart.pack(pady=35)
        self.cart_title.configure(text=f"Current Sale ({len(self.store.cart)})")
        for name, amount in (("Subtotal", self.store.subtotal), ("Discount", self.store.discount), ("Total", self.store.total)):
            text = T.money(amount)
            if self.totals[name].cget("text") != text:
                self.totals[name].configure(text=text)
        self.hold_button.configure(text="Resume" if self.store.held_cart else "Hold Sale")
        self.complete_button.configure(state="normal" if self.store.cart else "disabled")

    def focus_search(self):
        self.search.focus_set()
        self.search.select_range(0, "end")

    def scan(self, event=None):
        query = self.search.get().strip().lower()
        match = next((p for p in self.store.products if p["barcode"] == query or p["name"].lower() == query), None)
        if match:
            self.change_quantity(match["id"], 1)
            self.query.set("")
        else:
            self.app.toast("No exact product match.", "warning")

    def change_quantity(self, product_id, delta):
        try:
            self.store.change_quantity(product_id, delta)
            self.render_cart()
        except ValueError as error:
            self.app.toast(str(error), "warning")

    def remove(self, product_id):
        self.change_quantity(product_id, -self.store.cart[product_id])

    def clear(self):
        if self.store.cart:
            confirm(self.app, "Clear Cart", "Remove all items from the current sale?", self.clear_confirmed)

    def clear_confirmed(self):
        self.store.cart.clear()
        self.store.discount, self.store.cart_note = 0, ""
        self.render_cart()

    def apply_discount(self):
        if self.discount_entry.get().strip().upper() != "SAVE10":
            self.app.toast("Discount code not recognized.", "error")
        elif not self.store.cart:
            self.app.toast("Add products before applying a discount.", "warning")
        else:
            self.store.discount = self.store.subtotal * .1
            self.render_cart()

    def hold(self):
        self.store.hold_sale()
        self.render_cart()

    def edit_note(self):
        edit_text(self.app, "Sale Note", self.store.cart_note, lambda note: setattr(self.store, "cart_note", note))

    def checkout(self):
        if self.store.cart:
            return CheckoutDialog(self.app, self.completed)

    def completed(self, sale):
        self.render_cart()
        self.app.data_changed()
        return SaleCompletedDialog(self.app, sale)

    def destroy(self):
        if self.layout_job:
            self.after_cancel(self.layout_job)
        super().destroy()
