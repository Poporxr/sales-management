"""New Sale: the point-of-sale screen.

Left: searchable product tiles. Right: the cart with totals.
The cart lives only in this page (a plain dict); it is written to
the database once, at checkout, by shop.checkout().
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import database
import images
import shop
from ui import theme as T
from ui.widgets import label, button, entry, card, dropdown


class PosPage(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.content, fg_color="transparent")
        self.app = app
        self.cart = {}  # product_id -> quantity, the current sale draft

        label(self, "New Sale", 24, True).pack(anchor="w", pady=(0, 12))

        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.pack(fill="both", expand=True)
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_columnconfigure(1, weight=0)
        workspace.grid_rowconfigure(0, weight=1)

        # ---- left: product browser ----
        left = ctk.CTkFrame(workspace, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        filters = ctk.CTkFrame(left, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 10))
        self.search_var = tk.StringVar()
        self.search = entry(filters, "Search name or barcode...", width=260)
        self.search.pack(side="left", padx=(0, 8))
        self.search.configure(textvariable=self.search_var)
        # Enter on an exact barcode acts like a barcode scanner: the
        # product goes straight into the cart.
        self.search.bind("<Return>", self.scan_barcode)
        self.search_var.trace_add("write", lambda *_: self.render_products())
        self.category = dropdown(filters, ["All"] + database.list_categories(),
                                 command=lambda _: self.render_products(), width=150)
        self.category.pack(side="left", padx=(0, 8))
        self.sort = dropdown(filters, ["Name", "Price: low to high", "Stock: low to high"],
                             command=lambda _: self.render_products(), width=170)
        self.sort.pack(side="left")

        self.tiles = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.tiles.pack(fill="both", expand=True)

        # ---- right: cart ----
        cart_card = card(workspace, width=340)
        cart_card.grid(row=0, column=1, sticky="nsew")
        cart_card.pack_propagate(False)
        label(cart_card, "Current Sale", 16, True).pack(anchor="w", padx=16, pady=(14, 8))

        # Bottom section first so it stays pinned to the card's bottom:
        # totals and buttons never drift when the cart is empty.
        bottom = ctk.CTkFrame(cart_card, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=(0, 16))
        totals = ctk.CTkFrame(bottom, fg_color="transparent")
        totals.pack(fill="x", pady=(0, 10))
        self.subtotal_label = label(totals, "", 14)
        self.subtotal_label.pack(anchor="e")
        self.total_label = label(totals, "", 20, True)
        self.total_label.pack(anchor="e", pady=(4, 0))
        actions = ctk.CTkFrame(bottom, fg_color="transparent")
        actions.pack(fill="x")
        button(actions, "Checkout", self.open_checkout, width=150).pack(side="left")
        button(actions, "Clear", self.clear_cart, kind="secondary",
               width=90).pack(side="right")

        # Cart items take whatever space is left between title and bottom.
        self.cart_list = ctk.CTkScrollableFrame(cart_card, fg_color="transparent")
        self.cart_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.render_products()
        self.render_cart()

    # ------------------------------------------------- product tiles ---

    def filtered_products(self):
        """Products matching the search text, category, and sort choice."""
        query = self.search_var.get().strip().lower()
        products = database.list_products()
        if query:
            products = [p for p in products
                        if query in p["name"].lower() or query in p["barcode"]]
        chosen = self.category.get()
        if chosen != "All":
            products = [p for p in products if p["category"] == chosen]
        sort = self.sort.get()
        if sort.startswith("Price"):
            products.sort(key=lambda p: p["price"])
        elif sort.startswith("Stock"):
            products.sort(key=lambda p: p["stock"])
        else:
            products.sort(key=lambda p: p["name"].lower())
        return products

    def render_products(self):
        """Rebuild the product card grid. Simple beats clever: with a
        shop-sized catalog this is instant, and there is no stale-widget
        logic."""
        for child in self.tiles.winfo_children():
            child.destroy()
        products = self.filtered_products()
        # 2-column grid of product cards.
        for col in range(2):
            self.tiles.grid_columnconfigure(col, weight=1, uniform="cards")
        for index, product in enumerate(products):
            tile = card(self.tiles)
            tile.grid(row=index // 2, column=index % 2,
                       sticky="nsew", padx=6, pady=6)
            # Photo on top, centered. Fixed-height area keeps cards even
            # when a product has no photo.
            photo_area = ctk.CTkFrame(tile, fg_color="transparent", height=110)
            photo_area.pack(fill="x", pady=(12, 4))
            photo_area.pack_propagate(False)
            thumb = images.thumbnail(product.get("image"), 96)
            if thumb is not None:
                photo = label(photo_area, "")
                photo.configure(image=thumb)
                photo.image = thumb  # keep a reference or it disappears
                photo.pack(expand=True)
            label(tile, product["name"], 14, True, wraplength=150).pack(padx=10)
            label(tile, product["barcode"], 11, color=T.MUTED).pack(padx=10)
            label(tile, T.money(product["price"]), 16, True).pack(padx=10, pady=(2, 0))
            if product["stock"] == 0:
                label(tile, "Out of stock", 12, True, T.RED).pack(pady=(2, 10))
            else:
                label(tile, "In stock: %d" % product["stock"], 12,
                      color=T.MUTED).pack(pady=(2, 4))
                button(tile, "Add",
                       lambda pid=product["id"]: self.add_to_cart(pid),
                       width=120).pack(pady=(0, 12))

    def scan_barcode(self, event=None):
        """Enter key: if the text is an exact barcode, add that product."""
        code = self.search_var.get().strip()
        product = database.get_product_by_barcode(code)
        if product:
            self.add_to_cart(product["id"])
            self.search.delete(0, "end")
        else:
            messagebox.showwarning("Not found",
                                   "No product has the barcode '%s'." % code)

    # ---------------------------------------------------------- cart ---

    def add_to_cart(self, product_id):
        product = database.get_product(product_id)
        current = self.cart.get(product_id, 0)
        if current + 1 > product["stock"]:
            messagebox.showwarning("Stock",
                                   "Only %d of '%s' available."
                                   % (product["stock"], product["name"]))
            return
        self.cart[product_id] = current + 1
        self.render_cart()

    def change_quantity(self, product_id, delta):
        qty = self.cart.get(product_id, 0) + delta
        if qty <= 0:
            self.cart.pop(product_id, None)
        else:
            product = database.get_product(product_id)
            if qty > product["stock"]:
                messagebox.showwarning("Stock", "Only %d available." % product["stock"])
                return
            self.cart[product_id] = qty
        self.render_cart()

    def remove_item(self, product_id):
        self.cart.pop(product_id, None)
        self.render_cart()

    def clear_cart(self):
        self.cart = {}
        self.render_cart()

    def render_cart(self):
        for child in self.cart_list.winfo_children():
            child.destroy()
        if not self.cart:
            label(self.cart_list, "Cart is empty.", 13,
                  color=T.MUTED).pack(pady=20)
        for product_id, qty in self.cart.items():
            product = database.get_product(product_id)
            row = ctk.CTkFrame(self.cart_list, fg_color="transparent")
            row.pack(fill="x", pady=3)
            label(row, product["name"], 13, True).pack(anchor="w")
            label(row, "%s each" % T.money(product["price"]), 12,
                  color=T.MUTED).pack(anchor="w")
            controls = ctk.CTkFrame(row, fg_color="transparent")
            controls.pack(anchor="w", pady=(2, 0))
            button(controls, "-", lambda pid=product_id: self.change_quantity(pid, -1),
                   kind="secondary", width=36).pack(side="left", padx=(0, 4))
            label(controls, str(qty), 13, True, width=30).pack(side="left")
            button(controls, "+", lambda pid=product_id: self.change_quantity(pid, 1),
                   kind="secondary", width=36).pack(side="left", padx=(4, 0))
            button(controls, "Remove",
                   lambda pid=product_id: self.remove_item(pid),
                   kind="secondary", width=70).pack(side="left", padx=(8, 0))
            label(row, T.money(product["price"] * qty), 13, True).pack(anchor="e")
        total = shop.cart_total(self.cart)
        self.subtotal_label.configure(text="Subtotal: " + T.money(total))
        self.total_label.configure(text="Total: " + T.money(total))

    # ------------------------------------------------------ checkout ---

    def open_checkout(self):
        if not self.cart:
            messagebox.showwarning("Empty cart", "Add a product first.")
            return
        CheckoutDialog(self, self.cart)


class CheckoutDialog(ctk.CTkToplevel):
    """Payment dialog. Customer name is optional: leave it blank and the
    sale simply has no customer attached."""

    def __init__(self, page, cart):
        super().__init__(page)
        self.page = page
        self.cart = cart
        self.title("Checkout")
        self.geometry("380x460")
        self.transient(page)
        self.grab_set()  # modal: the sale screen waits for this dialog

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)

        total = shop.cart_total(cart)
        label(body, "Total: " + T.money(total), 22, True).pack(pady=(0, 16))

        label(body, "Customer name (optional)", 13, True).pack(anchor="w")
        self.customer = entry(body, "Walk-in customer", width=300)
        self.customer.pack(fill="x", pady=(0, 12))

        label(body, "Payment method", 13, True).pack(anchor="w")
        self.method = dropdown(body, ["Cash", "Transfer"],
                               command=self.on_method_change, width=300)
        self.method.pack(fill="x", pady=(0, 12))

        self.paid_label = label(body, "Amount received", 13, True)
        self.paid_label.pack(anchor="w")
        self.paid = entry(body, T.money(total).replace("\u20a6", ""), width=300)
        self.paid.pack(fill="x", pady=(0, 6))
        self.paid.bind("<KeyRelease>", self.update_change)
        self.change_label = label(body, "", 14, True, T.GREEN)
        self.change_label.pack(anchor="w", pady=(0, 16))

        button(body, "Complete Sale", self.complete).pack(fill="x", pady=(0, 8))
        button(body, "Cancel", self.destroy, kind="secondary").pack(fill="x")
        self.on_method_change("Cash")

    def on_method_change(self, choice):
        """Transfer means exact total: no amount field, no change."""
        if choice == "Cash":
            self.paid_label.pack(anchor="w")
            self.paid.pack(fill="x", pady=(0, 6))
        else:
            self.paid_label.pack_forget()
            self.paid.pack_forget()
        self.update_change()

    def update_change(self, event=None):
        if self.method.get() != "Cash":
            self.change_label.configure(text="")
            return
        try:
            paid = float(self.paid.get().replace(",", "") or 0)
        except ValueError:
            self.change_label.configure(text="")
            return
        total = shop.cart_total(self.cart)
        self.change_label.configure(
            text="Change: " + T.money(paid - total) if paid >= total else "")

    def complete(self):
        try:
            sale = shop.checkout(
                self.cart, self.method.get(), self.paid.get(),
                cashier=self.page.app.cashier,
                customer_name=self.customer.get())
        except ValueError as e:
            messagebox.showerror("Checkout failed", str(e))
            return
        self.page.clear_cart()
        self.destroy()
        # Show the receipt on screen. It is only a preview: the PDF is
        # generated if and when the user clicks Print.
        from ui.receipt_view import ReceiptPreview
        ReceiptPreview(self.page, sale, self.page.app.config)
        self.page.render_products()  # stock numbers changed, refresh tiles
