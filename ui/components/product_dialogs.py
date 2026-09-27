"""Product forms: validate locally, authorize sensitive edits, then commit once."""

from pathlib import Path
from tkinter import filedialog
from uuid import uuid4
import customtkinter as ctk
from PIL import Image, ImageOps
from ui import theme as T
from ui.components.widgets import (label, button, entry, select, badge, product_image,
                                   LOCAL_IMAGES)
from ui.components.dialogs import Dialog, ManagerDialog, confirm

CATEGORIES = ["Beverages", "Snacks", "Groceries", "Household", "Personal Care", "Others"]


class ProductDialog(Dialog):
    def __init__(self, app, product_id=None):
        self.product_id = product_id
        p = app.store.product(product_id) if product_id is not None else {}
        self.image_key = p.get("image", "")
        super().__init__(app, "Edit Product" if p else "Add Product", width=680, height=660,
                         subtitle="Enter product details for your inventory.", symbol="box")
        self.fields = {}
        top = ctk.CTkFrame(self.body, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))
        photo = ctk.CTkFrame(top, fg_color="transparent")
        photo.pack(side="left", padx=(0, 18))
        label(photo, "Product Image", 12, color=T.MUTED).pack(anchor="w")
        self.preview = ctk.CTkButton(photo, text="", image=product_image(self.image_key, 96),
                                     fg_color=T.BG, hover_color=T.BLUE_LIGHT, width=140, height=118,
                                     command=self.upload_image)
        self.preview.pack(pady=6)
        button(photo, "Choose Image", self.upload_image, "image", width=140, height=28).pack()
        details = ctk.CTkFrame(top, fg_color="transparent")
        details.pack(side="left", fill="x", expand=True)
        self.add_field(details, "name", "Product Name *", p.get("name", ""))
        self.add_field(details, "barcode", "Barcode / SKU *", p.get("barcode", ""))
        label(details, "Category *", 12, color=T.MUTED).pack(anchor="w")
        self.category = select(details, CATEGORIES)
        self.category.set(p.get("category", CATEGORIES[0]))
        self.category.pack(fill="x", pady=(4, 8))

        # Two compact rows match the reference while allowing the form body to
        # scroll on smaller desktops. Status is derived, never contradictory.
        grid = ctk.CTkFrame(self.body, fg_color="transparent")
        grid.pack(fill="x")
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="fields")
        for index, (field, caption, default) in enumerate([
            ("cost", "Cost Price *", 0), ("price", "Selling Price *", 0),
            ("unit", "Unit *", "Piece"), ("stock", "Current Stock *", 0),
            ("minimum", "Minimum Stock Alert", 10)]):
            group = ctk.CTkFrame(grid, fg_color="transparent")
            group.grid(row=index // 3, column=index % 3, sticky="ew", padx=(0, 10), pady=5)
            if field == "unit":
                label(group, caption, 12, color=T.MUTED).pack(anchor="w")
                self.unit = select(group, ["Piece", "Pack", "Carton", "Bottle", "Kg"], width=150)
                self.unit.set(p.get("unit", "Piece"))
                self.unit.pack(fill="x", pady=(4, 8))
            else:
                self.add_field(group, field, caption, p.get(field, default), width=140)
        state = ctk.CTkFrame(grid, fg_color="transparent")
        state.grid(row=1, column=2, sticky="ew", pady=5)
        label(state, "Status", 12, color=T.MUTED).pack(anchor="w")
        self.status = badge(state, "")
        self.status.pack(anchor="w", pady=8)
        for field in ("stock", "minimum"):
            self.fields[field].bind("<KeyRelease>", lambda event: self.update_status())
        self.update_status()
        label(self.body, "Description (Optional)", 12, color=T.MUTED).pack(anchor="w", pady=(10, 4))
        self.description = ctk.CTkTextbox(self.body, height=75, fg_color=T.BG, font=T.font(13), text_color=T.INK)
        self.description.pack(fill="x")
        self.description.insert("1.0", p.get("description", ""))
        self.error = label(self.body, "", 12, color=T.RED, wraplength=590, justify="left")
        self.error.pack(anchor="w", pady=8)
        self.actions("Save Changes" if p else "Add Product", self.save, "save")

    def add_field(self, parent, key, caption, value, width=220):
        label(parent, caption, 12, color=T.MUTED).pack(anchor="w")
        widget = entry(parent, "", width=width)
        widget.insert(0, str(value))
        widget.pack(fill="x", pady=(4, 8))
        self.fields[key] = widget

    def update_status(self):
        try:
            product = dict(stock=int(self.fields["stock"].get()), minimum=int(self.fields["minimum"].get()))
            status = self.app.store.stock_status(product)
            tone = T.GREEN if status == "In Stock" else T.RED
            self.status.configure(text=status, text_color=tone,
                                  fg_color=T.GREEN_LIGHT if status == "In Stock" else T.RED_LIGHT)
        except ValueError:
            self.status.configure(text="-")

    def upload_image(self):
        path = filedialog.askopenfilename(parent=self, title="Choose Product Image",
                                          filetypes=[("Product images", "*.png *.jpg *.jpeg")])
        if not path:
            return
        try:
            # No URLs are accepted. Keep a normalized copy in memory so deleting
            # or moving the original local file does not break this session.
            source_path = Path(path)
            if source_path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("Choose a PNG or JPG image no larger than 2 MB.")
            with Image.open(source_path) as source:
                if source.format not in ("PNG", "JPEG"):
                    raise ValueError("Choose a PNG or JPG image.")
                fitted = ImageOps.contain(ImageOps.exif_transpose(source).convert("RGBA"), (320, 320))
                square = Image.new("RGBA", (320, 320), "white")
                square.paste(fitted, ((320-fitted.width)//2, (320-fitted.height)//2), fitted)
            self.image_key = "upload-" + uuid4().hex
            LOCAL_IMAGES[self.image_key] = square
            self.preview.configure(image=product_image(self.image_key, 96))
            self.error.configure(text="")
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            self.error.configure(text=str(error))

    def save(self):
        values = {key: field.get().strip() for key, field in self.fields.items()}
        values.update(category=self.category.get(), unit=self.unit.get(), image=self.image_key,
                      description=self.description.get("1.0", "end").strip())
        try:
            validated = self.app.store.validate_product(values, self.product_id)
        except ValueError as error:
            self.error.configure(text=str(error))
            return
        def apply():
            try:
                self.app.store.save_product(validated, self.product_id)
            except ValueError as error:
                self.error.configure(text=str(error))
                return
            self.close()
            self.app.data_changed()
            if self.app.route == "product":
                self.app.navigate("product", product_id=self.product_id)
            self.app.toast("Product saved for this session.", "success")
        original = self.app.store.product(self.product_id) if self.product_id is not None else None
        if original and any(original[field] != validated[field] for field in ("price", "cost", "stock")):
            ManagerDialog(self.app, apply, "Price and stock changes require manager approval.")
        else:
            apply()


class StockDialog(Dialog):
    def __init__(self, app, product_id):
        self.product_id = product_id
        self.product = app.store.product(product_id)
        super().__init__(app, "Adjust Stock", width=630, height=580,
                         subtitle="Update stock quantity and record a reason for the change.")
        p = self.product
        top = ctk.CTkFrame(self.body, fg_color=T.BG, corner_radius=6)
        top.pack(fill="x", pady=(0, 16))
        label(top, "", image=product_image(p["image"], 62)).pack(side="left", padx=14, pady=12)
        text = ctk.CTkFrame(top, fg_color="transparent")
        text.pack(side="left")
        label(text, p["name"], 16, True).pack(anchor="w")
        label(text, p["barcode"], 12, color=T.MUTED).pack(anchor="w")
        label(top, f"Current Stock\n{p['stock']}", 16, True).pack(side="right", padx=20)
        label(self.body, "Adjustment Type", 13, color=T.MUTED).pack(anchor="w")
        self.mode = ctk.CTkSegmentedButton(self.body, values=["Add Stock", "Remove Stock", "Set Stock"],
                                         command=lambda _: self.update_preview(), height=36, font=T.font(13))
        self.mode.set("Add Stock")
        self.mode.pack(fill="x", pady=(6, 14))
        quantity = ctk.CTkFrame(self.body, fg_color="transparent")
        quantity.pack(fill="x")
        left = ctk.CTkFrame(quantity, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=(0, 16))
        label(left, "Quantity *", 13, color=T.MUTED).pack(anchor="w")
        self.quantity = entry(left, "0")
        self.quantity.insert(0, "0")
        self.quantity.pack(fill="x", pady=5)
        self.quantity.bind("<KeyRelease>", lambda event: self.update_preview())
        right = ctk.CTkFrame(quantity, fg_color="transparent")
        right.pack(side="left", fill="x", expand=True)
        label(right, "New Stock", 13, color=T.MUTED).pack(anchor="w")
        self.preview = label(right, str(p["stock"]), 22, True, T.GREEN, height=40)
        self.preview.pack(anchor="w", pady=5)
        label(self.body, "Reason *", 13, color=T.MUTED).pack(anchor="w", pady=(12, 4))
        self.reason = select(self.body, ["Select a reason", "Restock from supplier", "Damaged", "Stock count correction", "Returned stock", "Other"])
        self.reason.pack(fill="x")
        label(self.body, "Notes (Optional)", 13, color=T.MUTED).pack(anchor="w", pady=(12, 4))
        self.notes = ctk.CTkTextbox(self.body, height=70, fg_color=T.BG, text_color=T.INK, font=T.font(13))
        self.notes.pack(fill="x")
        self.error = label(self.body, "", 12, color=T.RED, wraplength=550, justify="left")
        self.error.pack(anchor="w", pady=8)
        self.actions("Update Stock", self.save, "box")

    def update_preview(self):
        try:
            quantity = int(self.quantity.get())
            value = self.product["stock"] + quantity if self.mode.get() == "Add Stock" else self.product["stock"] - quantity
            if self.mode.get() == "Set Stock":
                value = quantity
            self.preview.configure(text=str(value), text_color=T.RED if value < 0 else T.GREEN)
        except ValueError:
            self.preview.configure(text="-")

    def save(self):
        try:
            quantity = int(self.quantity.get())
            if quantity < 0 or self.reason.get() == "Select a reason":
                raise ValueError
            notes = self.notes.get("1.0", "end").strip()
            if len(notes) > 200:
                self.error.configure(text="Keep notes to 200 characters or fewer.")
                return
        except ValueError:
            self.error.configure(text="Enter a non-negative whole quantity and choose a reason.")
            return
        def apply():
            try:
                self.app.store.adjust_stock(self.product_id, self.mode.get(), quantity, self.reason.get(), notes)
            except ValueError as error:
                self.error.configure(text=str(error))
                return
            self.close()
            self.app.data_changed()
            if self.app.route == "product":
                self.app.navigate("product", product_id=self.product_id)
            self.app.toast("Stock updated for this session.", "success")
        ManagerDialog(self.app, apply, "Adjusting stock requires manager approval.")


def delete_product(app, product_id):
    """Confirmation and authorization are both cancellable before any mutation."""
    product = app.store.product(product_id)
    def remove():
        app.store.delete_product(product_id)
        app.data_changed()
        if app.route == "product":
            app.navigate("products")
        app.toast("Product removed from this session.", "success")
    return confirm(app, "Delete Product", f"Delete {product['name']}? Existing sale receipts will be retained.",
                   lambda: ManagerDialog(app, remove, "Deleting a product requires manager approval."))
