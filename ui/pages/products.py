"""Products: the shop's catalog.

Searchable list with Add, Edit, Stock, and Delete actions.
Edit, Stock, and Delete ask for the manager PIN first: one small
dialog, one small check, clearly marked as demo-only.
"""

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

import database
import images
import shop
from ui import theme as T
from ui.widgets import label, button, entry, card, dropdown


class ProductsPage(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.content, fg_color="transparent")
        self.app = app

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        label(header, "Products", 24, True).pack(side="left")
        button(header, "Add Product",
               lambda: ProductDialog(self), width=140).pack(side="right")

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 10))
        self.search_var = tk.StringVar()
        search = entry(filters, "Search name or barcode...", width=260)
        search.pack(side="left", padx=(0, 8))
        search.configure(textvariable=self.search_var)
        self.search_var.trace_add("write", lambda *_: self.render())
        self.category = dropdown(filters, ["All"] + database.list_categories(),
                                 command=lambda _: self.render(), width=150)
        self.category.pack(side="left")

        self.rows = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rows.pack(fill="both", expand=True)
        self.render()

    def render(self):
        """Rebuild the product card grid. Fresh from the database every time."""
        for child in self.rows.winfo_children():
            child.destroy()
        query = self.search_var.get().strip().lower()
        products = database.list_products()
        if query:
            products = [p for p in products
                        if query in p["name"].lower() or query in p["barcode"]]
        chosen = self.category.get()
        if chosen != "All":
            products = [p for p in products if p["category"] == chosen]
        if not products:
            label(self.rows, "No products found.", 14,
                  color=T.MUTED).pack(pady=20)
            return
        for col in range(3):
            self.rows.grid_columnconfigure(col, weight=1, uniform="cards")
        for index, product in enumerate(products):
            row = card(self.rows)
            row.grid(row=index // 3, column=index % 3,
                     sticky="nsew", padx=6, pady=6)
            # Photo on top, centered. Fixed-height area keeps cards even
            # when a product has no photo.
            photo_area = ctk.CTkFrame(row, fg_color="transparent", height=110)
            photo_area.pack(fill="x", pady=(12, 4))
            photo_area.pack_propagate(False)
            thumb = images.thumbnail(product.get("image"), 96)
            if thumb is not None:
                photo = label(photo_area, "")
                photo.configure(image=thumb)
                photo.image = thumb  # keep a reference or it disappears
                photo.pack(expand=True)
            label(row, product["name"], 14, True, wraplength=150).pack(padx=10)
            label(row, "%s  |  %s" % (product["barcode"], product["category"]),
                  11, color=T.MUTED).pack(padx=10)
            label(row, "%s   |   Stock: %d" % (T.money(product["price"]), product["stock"]),
                  13, True).pack(padx=10, pady=(2, 6))
            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(pady=(0, 12))
            button(actions, "Edit",
                   lambda p=product: self.guarded(p, "edit"), kind="secondary",
                   width=70).pack(side="left", padx=3)
            button(actions, "Stock",
                   lambda p=product: self.guarded(p, "stock"), kind="secondary",
                   width=70).pack(side="left", padx=3)
            button(actions, "Delete",
                   lambda p=product: self.guarded(p, "delete"), kind="danger",
                   width=70).pack(side="left", padx=3)

    def guarded(self, product, action):
        """Ask for the manager PIN before a sensitive action."""
        dialog = PinDialog(self)
        self.wait_window(dialog)
        if not dialog.ok:
            return  # wrong PIN or cancelled: nothing happens
        if action == "edit":
            ProductDialog(self, product)
        elif action == "stock":
            StockDialog(self, product)
        elif action == "delete":
            if messagebox.askyesno("Delete",
                                    "Delete '%s' permanently?" % product["name"]):
                shop.delete_product(product["id"], self.app.cashier)
                self.render()


class PinDialog(ctk.CTkToplevel):
    """One small PIN gate. Demo only, not real security."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manager PIN")
        self.geometry("300x190")
        self.transient(parent)
        self.grab_set()
        self.ok = False

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)
        label(body, "Enter manager PIN", 14, True).pack(pady=(0, 10))
        self.pin = entry(body, "", width=200)
        self.pin.configure(show="*", justify="center")
        self.pin.pack(pady=(0, 6))
        self.pin.bind("<Return>", lambda e: self.submit())
        self.error = label(body, "", 12, color=T.RED)
        self.error.pack()
        button(body, "Unlock", self.submit, width=200).pack(pady=(8, 0))
        self.pin.focus_set()

    def submit(self):
        if shop.check_pin(self.pin.get()):
            self.ok = True
            self.destroy()
        else:
            self.error.configure(text="Wrong PIN, try again.")
            self.pin.delete(0, "end")


class ProductDialog(ctk.CTkToplevel):
    """Add or edit a product. Same form, same validation, both ways."""

    def __init__(self, page, product=None):
        super().__init__(page)
        self.page = page
        self.product = product
        self.title("Edit Product" if product else "Add Product")
        self.geometry("400x720")
        self.transient(page)
        self.grab_set()
        # Filename of the chosen photo (in assets/products/), or "".
        self.image_file = (product or {}).get("image", "")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # Photo picker with a small preview.
        label(body, "Photo (optional)", 13, True).pack(anchor="w")
        photo_row = ctk.CTkFrame(body, fg_color="transparent")
        photo_row.pack(fill="x", pady=(0, 4))
        self.photo_preview = label(photo_row, "No photo", 12, color=T.MUTED)
        self.photo_preview.pack(side="left", padx=(0, 10))
        button(photo_row, "Choose Image", self.choose_image,
               kind="secondary", width=130).pack(side="left")
        self.show_preview()

        self.fields = {}
        rows = [("name", "Name"), ("barcode", "Barcode"),
                ("category", "Category"), ("price", "Price"),
                ("cost", "Cost"), ("stock", "Stock"),
                ("brand", "Brand"), ("unit", "Unit")]
        for key, title in rows:
            label(body, title, 13, True).pack(anchor="w", pady=(8, 0))
            e = entry(body, "", width=320)
            e.pack(fill="x")
            if product:
                e.insert(0, str(product.get(key, "")))
            self.fields[key] = e

        button(body, "Save", self.save).pack(fill="x", pady=(18, 8))
        button(body, "Cancel", self.destroy, kind="secondary").pack(fill="x")

    def show_preview(self):
        """Show the current photo thumbnail, or 'No photo'."""
        thumb = images.thumbnail(self.image_file, 56)
        if thumb is None:
            self.photo_preview.configure(image=None, text="No photo")
            self.photo_preview.image = None
        else:
            self.photo_preview.configure(image=thumb, text="")
            self.photo_preview.image = thumb  # keep a reference

    def choose_image(self):
        """Let the user pick a photo and copy it into assets/products/."""
        path = filedialog.askopenfilename(
            title="Choose product photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
        if not path:
            return  # user cancelled
        try:
            self.image_file = images.save_upload(path)
        except ValueError as e:
            messagebox.showerror("Bad image", str(e))
            return
        self.show_preview()

    def save(self):
        values = {k: e.get() for k, e in self.fields.items()}
        values["image"] = self.image_file
        try:
            if self.product:
                shop.update_product(self.product["id"], values,
                                    self.page.app.cashier)
            else:
                shop.add_product(values, self.page.app.cashier)
        except ValueError as e:
            messagebox.showerror("Cannot save", str(e))
            return
        self.destroy()
        self.page.render()


class StockDialog(ctk.CTkToplevel):
    """Change stock with a required reason. The reason lands in the
    audit log so the change is always explainable later."""

    def __init__(self, page, product):
        super().__init__(page)
        self.page = page
        self.product = product
        self.title("Adjust Stock")
        self.geometry("360x400")
        self.transient(page)
        self.grab_set()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)
        label(body, product["name"], 16, True).pack(pady=(0, 4))
        label(body, "Current stock: %d" % product["stock"], 13,
              color=T.MUTED).pack(pady=(0, 12))

        label(body, "Mode", 13, True).pack(anchor="w")
        self.mode = dropdown(body, ["Add", "Remove", "Set"], width=300)
        self.mode.pack(fill="x", pady=(0, 12))

        label(body, "Quantity", 13, True).pack(anchor="w")
        self.quantity = entry(body, "", width=300)
        self.quantity.pack(fill="x", pady=(0, 12))

        label(body, "Reason (required)", 13, True).pack(anchor="w")
        self.reason = entry(body, "e.g. delivery received", width=300)
        self.reason.pack(fill="x", pady=(0, 12))

        button(body, "Apply", self.apply).pack(fill="x", pady=(6, 8))
        button(body, "Cancel", self.destroy, kind="secondary").pack(fill="x")

    def apply(self):
        try:
            shop.adjust_stock(self.product["id"], self.mode.get(),
                              self.quantity.get(), self.reason.get(),
                              self.page.app.cashier)
        except ValueError as e:
            messagebox.showerror("Cannot adjust stock", str(e))
            return
        self.destroy()
        self.page.render()
