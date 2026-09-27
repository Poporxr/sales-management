import tkinter as tk
import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import Page, label, panel, button, entry, select, badge, product_image, icon_button
from ui.components.dialogs import CheckoutDialog, confirm

CATEGORIES = ["All", "Beverages", "Snacks", "Groceries", "Household", "Personal Care", "Others"]


class SalePage(Page):
    def __init__(self, app, catalog=False):
        super().__init__(app)
        self.catalog = catalog
        self.category = "All"
        self.columns = 3
        self.layout_job = None
        self.query = tk.StringVar()
        header = self.heading("Products" if catalog else "New Sale",
                              "Product catalog" if catalog else "Scan a barcode, search for a product or select from the list.")
        if not catalog:
            button(header, "Scan Barcode", self.focus_search, "scan", width=150).pack(side="right")
        columns = ctk.CTkFrame(self.body, fg_color="transparent")
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=1)
        columns.grid_rowconfigure(0, weight=1)
        self.catalog_panel = ctk.CTkFrame(columns, fg_color="transparent")
        self.catalog_panel.grid(row=0, column=0, sticky="nsew")
        filters = ctk.CTkFrame(self.catalog_panel, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 12))
        self.search = entry(filters, "Search product name or barcode...", self.query)
        self.search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search.bind("<Return>", self.scan)
        self.sort = select(filters, ["Sort: Name", "Price: Low to High", "Stock: Low to High"], lambda _: self.render_products(), width=150)
        self.sort.pack(side="right")
        categories = ctk.CTkFrame(self.catalog_panel, fg_color="transparent")
        categories.pack(fill="x", pady=(0, 12))
        self.category_select = select(categories, ["All Categories"] + CATEGORIES[1:], self.select_category, width=175)
        self.category_select.pack(side="left")
        self.count_label = label(categories, "", 12, color=T.MUTED)
        self.count_label.pack(side="right")
        self.products_frame = ctk.CTkFrame(self.catalog_panel, fg_color="transparent")
        self.products_frame.pack(fill="both", expand=True)
        self.products_frame.bind("<Configure>", self.resize_grid)
        if not catalog:
            columns.grid_columnconfigure(1, minsize=360)
            self.cart_panel = panel(columns, width=360)
            self.cart_panel.grid(row=0, column=1, sticky="nsew", padx=(16, 0))
            self.cart_panel.grid_columnconfigure(0, weight=1)
            self.render_cart()
        self.query.trace_add("write", lambda *_: self.render_products())
        self.render_products()

    def destroy(self):
        if self.layout_job:
            self.after_cancel(self.layout_job)
        super().destroy()

    def focus_search(self):
        self.search.focus_set()
        self.search.select_range(0, "end")

    def scan(self, event=None):
        query = self.query.get().strip().lower()
        matches = [p for p in self.store.products if p["barcode"] == query or p["name"].lower() == query]
        if len(matches) == 1:
            if self.catalog:
                self.app.navigate("product", product_id=matches[0]["id"])
            else:
                self.change_quantity(matches[0]["id"], 1)
                self.query.set("")
        else:
            self.app.toast("No exact product match. Select a product from the results.", "warning")

    def select_category(self, value):
        self.category = "All" if value == "All Categories" else value
        self.render_products()

    def resize_grid(self, event):
        logical_width = event.width / self._get_widget_scaling()
        columns = max(2, min(4 if self.catalog else 3, int(logical_width // 225)))
        if columns != self.columns:
            self.columns = columns
            if self.layout_job:
                self.after_cancel(self.layout_job)
            self.layout_job = self.after(80, self.render_products)

    def render_products(self):
        self.layout_job = None
        for widget in self.products_frame.winfo_children():
            widget.destroy()
        for i in range(4):
            self.products_frame.grid_columnconfigure(i, weight=0, minsize=0, uniform="")
        query = self.query.get().strip().lower()
        products = [p for p in self.store.products if
                    (query in p["name"].lower() or query in p["barcode"]) and
                    (self.category == "All" or p["category"] == self.category)]
        key = {"Sort: Name": "name", "Price: Low to High": "price", "Stock: Low to High": "stock"}[self.sort.get()]
        products.sort(key=lambda p: p[key])
        self.count_label.configure(text=f"{len(products)} products")
        if not products:
            label(self.products_frame, "No products found", 18, color=T.MUTED).pack(pady=80)
            return
        for i in range(self.columns):
            self.products_frame.grid_columnconfigure(i, weight=1, uniform="products")
        for i, product in enumerate(products):
            tile = ctk.CTkFrame(self.products_frame, fg_color=T.WHITE, border_width=1,
                                border_color=T.LINE, corner_radius=8, height=164)
            tile.grid(row=i // self.columns, column=i % self.columns, sticky="nsew", padx=4, pady=4)
            tile.grid_columnconfigure(1, weight=1)
            photo = label(tile, "", image=product_image(product["image"], 67), cursor="hand2")
            photo.grid(row=0, column=0, rowspan=3, padx=(10, 8), pady=14)
            photo.bind("<Button-1>", lambda event, p=product: self.app.navigate("product", product_id=p["id"]))
            name = label(tile, product["name"], 12, True, wraplength=125, cursor="hand2")
            name.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(15, 0))
            name.bind("<Button-1>", lambda event, p=product: self.app.navigate("product", product_id=p["id"]))
            label(tile, product["barcode"], 10, color=T.MUTED).grid(row=1, column=1, sticky="w", padx=(0, 8))
            label(tile, T.money(product["price"]), 18, True).grid(row=2, column=1, sticky="w", pady=(0, 5))
            bottom = ctk.CTkFrame(tile, fg_color="transparent")
            bottom.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 12))
            badge(bottom, f"In stock: {product['stock']}", "amber" if product["stock"] <= product["minimum"] else "green").pack(side="left")
            if self.catalog:
                icon_button(bottom, "eye", lambda p=product: self.app.navigate("product", product_id=p["id"]), "View product details").pack(side="right")
            else:
                icon_button(bottom, "plus", lambda p=product: self.change_quantity(p["id"], 1), "Add to sale").pack(side="right")
        self.update_idletasks()
        self._parent_canvas.yview_moveto(0)

    def change_quantity(self, product_id, delta):
        try:
            self.store.change_quantity(product_id, delta)
        except ValueError as error:
            self.app.toast(str(error), "warning")
        self.render_cart()

    def remove(self, product_id):
        self.store.change_quantity(product_id, -self.store.cart[product_id])
        self.render_cart()

    def clear(self):
        if self.store.cart:
            confirm(self.app, "Clear Cart", "Remove all items from the current sale?", self.clear_confirmed)

    def clear_confirmed(self):
        self.store.cart.clear()
        self.store.discount = 0
        self.render_cart()

    def render_cart(self):
        for child in self.cart_panel.winfo_children():
            child.destroy()
        body = ctk.CTkFrame(self.cart_panel, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x", pady=(0, 15))
        label(top, f"Current Sale ({len(self.store.cart)} items)", 16, True).pack(side="left")
        icon_button(top, "delete", self.clear, "Clear cart", "danger").pack(side="right")
        for pid, quantity in self.store.cart.items():
            product = self.store.product(pid)
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=(0, 12))
            row.grid_columnconfigure(1, weight=1)
            label(row, "", image=product_image(product["image"], 43)).grid(row=0, column=0, rowspan=2, padx=(0, 10))
            label(row, product["name"], 12, True).grid(row=0, column=1, sticky="w")
            label(row, f"{T.money(product['price'])} each", 11, color=T.MUTED).grid(row=1, column=1, sticky="w")
            icon_button(row, "close", lambda p=pid: self.remove(p), "Remove item", "neutral", 26).grid(row=0, column=2)
            controls = ctk.CTkFrame(row, fg_color="transparent")
            controls.grid(row=2, column=1, sticky="w", pady=(7, 0))
            icon_button(controls, "minus", lambda p=pid: self.change_quantity(p, -1), "Decrease quantity", "neutral", 28).pack(side="left")
            label(controls, str(quantity), 13, True, width=30, anchor="center").pack(side="left")
            icon_button(controls, "plus", lambda p=pid: self.change_quantity(p, 1), "Increase quantity", "neutral", 28).pack(side="left")
            label(row, T.money(product["price"] * quantity), 14, True).grid(row=2, column=2, sticky="e", padx=(4, 0))
            ctk.CTkFrame(body, fg_color=T.LINE, height=1).pack(fill="x", pady=(0, 12))
        if not self.store.cart:
            label(body, "Your cart is empty", 16, color=T.MUTED).pack(pady=65)
        discount_row = ctk.CTkFrame(body, fg_color="transparent")
        discount_row.pack(fill="x", pady=(4, 15))
        self.discount_entry = entry(discount_row, "Discount code", width=170)
        self.discount_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        button(discount_row, "Apply", self.apply_discount, width=60).pack(side="right")
        for name, amount in [("Subtotal", self.store.subtotal), ("Discount", self.store.discount)]:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=3)
            label(row, name, color=T.MUTED).pack(side="left")
            label(row, T.money(amount), color=T.MUTED).pack(side="right")
        total = ctk.CTkFrame(body, fg_color=T.BLUE_LIGHT, corner_radius=8)
        total.pack(fill="x", pady=(14, 24))
        label(total, "Total", 20, True, T.BLUE).pack(side="left", padx=12, pady=15)
        label(total, T.money(self.store.total), 25, True, T.BLUE).pack(side="right", padx=12)
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x")
        button(actions, "Resume" if self.store.held_cart else "Hold Sale", self.hold, "clock", width=100).pack(side="left", padx=(0, 8))
        complete = button(actions, "Complete Sale", self.checkout, "money", kind="primary", width=180)
        complete.pack(side="right", fill="x", expand=True)
        complete.configure(state="normal" if self.store.cart else "disabled")

    def apply_discount(self):
        if self.discount_entry.get().strip().upper() != "SAVE10":
            self.app.toast("Discount code not recognized.", "error")
            return
        if not self.store.cart:
            self.app.toast("Add products before applying a discount.", "warning")
            return
        self.store.discount = round(self.store.subtotal * .1)
        self.render_cart()
        self.app.toast("10% discount applied to the current subtotal.", "success")

    def hold(self):
        current = (dict(self.store.cart), self.store.discount)
        if self.store.held_cart:
            self.store.cart, self.store.discount = self.store.held_cart
            self.store.held_cart = current if current[0] else None
            self.app.toast("Held sale resumed.", "success")
        elif self.store.cart:
            self.store.held_cart = current
            self.store.cart = {}
            self.store.discount = 0
            self.app.toast("Sale held for this session.", "success")
        self.render_cart()

    def checkout(self):
        if self.store.cart:
            return CheckoutDialog(self.app, self.completed)

    def completed(self, sale):
        self.app.navigate("sale", sale_id=sale["id"])
        self.app.toast(f"Sale completed. Change: {T.money(sale['paid']-sale['total'])}", "success")
