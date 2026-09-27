from datetime import datetime
import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import (Page, Table, Chart, label, panel, button, badge,
                                   product_image, key_values, icon_button, entry, select)
from ui.components.dialogs import number_form, edit_text, confirm


def section(parent, title):
    frame = panel(parent)
    frame.pack(fill="x", pady=(0, 14))
    label(frame, title, 17, True).pack(anchor="w", padx=18, pady=(14, 8))
    body = ctk.CTkFrame(frame, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=18, pady=(0, 16))
    return body


def item_table(parent, items, compact=False):
    columns = ["Product", "Barcode", "Qty", "Unit Price", "Total"]
    table = Table(parent, columns, [5, 4, 1, 2, 2])
    table.pack(fill="x")
    for item in items:
        def product_cell(frame, p=item):
            cell = ctk.CTkFrame(frame, fg_color="transparent")
            label(cell, "", image=product_image(p["image"], 31 if compact else 44)).pack(side="left", padx=(0, 10))
            label(cell, p["name"], 11 if compact else 12, True, wraplength=115).pack(side="left")
            return cell
        table.add([product_cell,
                   lambda f, p=item: label(f, p["barcode"], 10 if compact else 11, color=T.MUTED),
                   item["quantity"], T.money(item["price"]), T.money(item["quantity"] * item["price"])])


class ProductDetails(Page):
    def __init__(self, app, product_id):
        super().__init__(app)
        self.product = self.store.product(product_id)
        p = self.product
        top = ctk.CTkFrame(self.body, fg_color="transparent")
        top.pack(fill="x", pady=(0, 16))
        button(top, "Back to Products", lambda: app.navigate("products"), "back", kind="neutral", width=170).pack(side="left")
        button(top, "Delete Product", self.delete, "delete", kind="danger", width=150).pack(side="right")
        overview = panel(self.body)
        overview.pack(fill="x", pady=(0, 14))
        overview.grid_columnconfigure(1, weight=1)
        label(overview, "", image=product_image(p["image"], 145)).grid(row=0, column=0, rowspan=3, padx=20, pady=20)
        name = ctk.CTkFrame(overview, fg_color="transparent")
        name.grid(row=0, column=1, sticky="w", pady=(18, 0))
        label(name, p["name"], 27, True).pack(side="left", padx=(0, 14))
        badge(name, "Low Stock" if p["stock"] <= p["minimum"] else "In Stock",
              "amber" if p["stock"] <= p["minimum"] else "green").pack(side="left")
        code = ctk.CTkFrame(overview, fg_color="transparent")
        code.grid(row=1, column=1, sticky="w")
        label(code, p["barcode"], 14, color=T.MUTED).pack(side="left", padx=(0, 10))
        icon_button(code, "copy", self.copy_barcode, "Copy barcode", size=28).pack(side="left")
        metadata = ctk.CTkFrame(overview, fg_color="transparent")
        metadata.grid(row=2, column=1, sticky="ew", pady=(5, 20))
        for title, value in [("Category", p["category"]), ("Brand", p["brand"]), ("Unit", p["unit"])]:
            group = ctk.CTkFrame(metadata, fg_color="transparent")
            group.pack(side="left", padx=(0, 40))
            label(group, title, 12, color=T.MUTED).pack(anchor="w")
            label(group, value, 13, True).pack(anchor="w")
        stock = ctk.CTkFrame(overview, fg_color=T.BG, corner_radius=8)
        stock.grid(row=0, column=2, rowspan=3, padx=18, pady=18, sticky="nsew")
        label(stock, "Current Stock", 13, color=T.MUTED).pack(anchor="w", padx=20, pady=(14, 0))
        label(stock, f"{p['stock']} pieces", 25, True).pack(anchor="w", padx=20)
        label(stock, f"Minimum stock: {p['minimum']}", 12, color=T.MUTED).pack(anchor="w", padx=20, pady=(8, 18))
        self.tabs = ctk.CTkSegmentedButton(self.body, values=["Overview", "Stock History", "Price History", "Sales History", "Edit Product"],
                                          command=self.show_tab, font=T.font(13), height=42,
                                          fg_color=T.LINE, selected_color=T.BLUE,
                                          selected_hover_color=T.BLUE, unselected_color=T.WHITE,
                                          unselected_hover_color=T.BLUE_LIGHT, text_color=T.INK,
                                          text_color_disabled=T.MUTED)
        self.tabs.pack(fill="x", pady=(0, 14))
        self.tab_body = ctk.CTkFrame(self.body, fg_color="transparent")
        self.tab_body.pack(fill="both", expand=True)
        self.tabs.set("Overview")
        self.show_tab("Overview")

    def copy_barcode(self):
        self.app.clipboard_clear()
        self.app.clipboard_append(self.product["barcode"])
        self.app.toast("Barcode copied.", "success")

    def matching_sales(self):
        result = []
        for sale in self.store.sales:
            for item in sale["items"]:
                if item["id"] == self.product["id"]:
                    result.append((sale, item))
        return result

    def show_tab(self, tab):
        for widget in self.tab_body.winfo_children():
            widget.destroy()
        if tab == "Edit Product":
            self.edit_form()
            return
        if tab in ("Stock History", "Price History"):
            field = "stock" if tab == "Stock History" else "price"
            body = section(self.tab_body, tab)
            table = Table(body, ["Date & Time", "Previous", "New Value", "User"], [3, 2, 2, 2])
            table.pack(fill="x")
            changes = self.product.get(field + "_history", [])
            for change in reversed(changes):
                formatter = T.money if field == "price" else str
                table.add([change["date"].strftime("%d %b %Y, %I:%M %p"), formatter(change["old"]), formatter(change["new"]), "Admin"])
            if not changes:
                label(body, "No changes recorded", 14, color=T.MUTED).pack(pady=30)
            return
        if tab == "Sales History":
            self.sales_table(section(self.tab_body, "Sales History"))
            return
        p = self.product
        metrics = ctk.CTkFrame(self.tab_body, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, 14))
        for i, (name, value, action) in enumerate([
            ("Selling Price", T.money(p["price"]), lambda: self.change("price", "Change Price", "Selling price")),
            ("Cost Price", T.money(p["cost"]), lambda: self.change("cost", "Edit Cost Price", "Cost price")),
            ("Total Sold", f"{sum(item['quantity'] for _, item in self.matching_sales())} pieces", None)]):
            metrics.grid_columnconfigure(i, weight=1, uniform="price")
            tile = panel(metrics)
            tile.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            text = ctk.CTkFrame(tile, fg_color="transparent")
            text.pack(side="left", padx=18, pady=14)
            label(text, name, 12, color=T.MUTED).pack(anchor="w")
            label(text, value, 23, True).pack(anchor="w")
            if action:
                icon_button(tile, "edit", action, name).pack(side="right", padx=14)
        columns = ctk.CTkFrame(self.tab_body, fg_color="transparent")
        columns.pack(fill="x")
        columns.grid_columnconfigure(0, weight=7, uniform="detail")
        columns.grid_columnconfigure(1, weight=3, uniform="detail")
        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right = ctk.CTkFrame(columns, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        chart = section(left, "Sales Trend (Last 7 Trading Days)")
        matches = self.matching_sales()
        latest = max((sale["date"].date() for sale, _ in matches), default=datetime.now().date())
        from datetime import timedelta
        days = [latest - timedelta(days=i) for i in reversed(range(7))]
        quantities = [sum(item["quantity"] for sale, item in matches if sale["date"].date() == day) for day in days]
        Chart(chart, quantities, [d.strftime("%b %d") for d in days], bars=True, height=175).pack(fill="x")
        self.sales_table(section(left, "Recent Sales"), limit=5)
        quick = section(right, "Quick Actions")
        for text, action, symbol, kind in [
            ("Add to Sale", self.add_to_sale, "cart", "soft"),
            ("Adjust Stock", lambda: self.change("stock", "Adjust Stock", "New stock quantity", True), "box", "green"),
            ("Edit Product", self.select_edit, "edit", "neutral"),
            ("Delete Product", self.delete, "delete", "danger")]:
            button(quick, text, action, symbol, kind=kind).pack(fill="x", pady=4)
        stock = section(right, "Stock Information")
        key_values(stock, [("Current Stock", f"{p['stock']} pieces"), ("Minimum Stock", f"{p['minimum']} pieces"),
                           ("Unit", p["unit"]), ("Created", "12 Aug 2025")])

    def sales_table(self, body, limit=None):
        table = Table(body, ["Date & Time", "Quantity", "Unit Price", "Total"], [4, 2, 2, 2])
        table.pack(fill="x")
        for sale, item in self.matching_sales()[:limit]:
            table.add([sale["date"].strftime("%d %b %Y, %I:%M %p"), item["quantity"], T.money(item["price"]),
                       T.money(item["quantity"] * item["price"])], lambda s=sale: self.app.navigate("sale", sale_id=s["id"]))

    def add_to_sale(self):
        try:
            self.store.change_quantity(self.product["id"], 1)
            self.app.navigate("pos")
        except ValueError as error:
            self.app.toast(str(error), "warning")

    def select_edit(self):
        self.tabs.set("Edit Product")
        self.show_tab("Edit Product")

    def change(self, field, title, caption, integer=False):
        def save(value):
            if field == "stock" and value < self.store.cart.get(self.product["id"], 0):
                self.app.toast("Remove reserved items from the cart before reducing stock.", "warning")
                return
            self.product.setdefault(field + "_history", []).append(dict(date=datetime.now(), old=self.product[field], new=value))
            self.product[field] = value
            self.app.navigate("product", product_id=self.product["id"])
            self.app.toast("Product updated for this session.", "success")
        number_form(self.app, title, caption, self.product[field], save, integer)

    def delete(self):
        def remove():
            pid = self.product["id"]
            self.store.cart.pop(pid, None)
            if self.store.held_cart:
                self.store.held_cart[0].pop(pid, None)
            self.store.products.remove(self.product)
            self.store.discount = 0
            self.app.navigate("products")
            self.app.toast("Product removed from this session.", "success")
        confirm(self.app, "Delete Product", f"Delete {self.product['name']}? Existing sale receipts will be retained.", remove)

    def edit_form(self):
        body = section(self.tab_body, "Edit Product")
        fields = {}
        form = ctk.CTkFrame(body, fg_color="transparent")
        form.pack(fill="x")
        for i, (field, caption) in enumerate([("name", "Product name"), ("barcode", "Barcode / SKU"),
                                              ("brand", "Brand"), ("unit", "Unit"), ("minimum", "Minimum stock")]):
            form.grid_columnconfigure(i % 2, weight=1)
            group = ctk.CTkFrame(form, fg_color="transparent")
            group.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 20), pady=8)
            label(group, caption, 12, color=T.MUTED).pack(anchor="w")
            field_entry = entry(group, caption)
            field_entry.pack(fill="x", pady=5)
            field_entry.insert(0, str(self.product[field]))
            fields[field] = field_entry
        label(body, "Category", 12, color=T.MUTED).pack(anchor="w", pady=(10, 5))
        category = select(body, ["Beverages", "Snacks", "Groceries", "Household", "Personal Care", "Others"])
        category.set(self.product["category"])
        category.pack(anchor="w")
        error = label(body, "", 12, color=T.RED)
        error.pack(anchor="w", pady=8)

        def save():
            values = {key: widget.get().strip() for key, widget in fields.items()}
            if any(not value for value in values.values()):
                error.configure(text="Complete all fields.")
                return
            try:
                values["minimum"] = int(values["minimum"])
                if values["minimum"] < 0:
                    raise ValueError
            except ValueError:
                error.configure(text="Minimum stock must be a non-negative whole number.")
                return
            if any(p["id"] != self.product["id"] and p["barcode"] == values["barcode"] for p in self.store.products):
                error.configure(text="Another product already has this barcode.")
                return
            self.product.update(values, category=category.get())
            self.app.navigate("product", product_id=self.product["id"])
            self.app.toast("Product updated for this session.", "success")
        button(body, "Save Changes", save, "save", kind="primary").pack(anchor="e")


class SaleDetails(Page):
    def __init__(self, app, sale_id):
        super().__init__(app)
        self.sale = self.store.sale(sale_id)
        sale = self.sale
        header = self.heading("Sale Details", f"Transaction #{sale_id}", ("Back to Sales History", lambda: app.navigate("sales")))
        button(header, "Print Receipt", self.print_receipt, "print", width=150).pack(side="right")
        columns = ctk.CTkFrame(self.body, fg_color="transparent")
        columns.pack(fill="x")
        columns.grid_columnconfigure(0, weight=1)
        columns.grid_columnconfigure(1, minsize=310)
        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        right = panel(columns, width=310)
        right.grid(row=0, column=1, sticky="nsew")
        metadata = panel(left)
        metadata.pack(fill="x", pady=(0, 14))
        for i, (title, value) in enumerate([("Date & Time", sale["date"].strftime("%d %b %Y, %I:%M %p")),
                                           ("Payment", sale["payment"]), ("Status", sale["status"]), ("Cashier", sale["cashier"])]):
            metadata.grid_columnconfigure(i, weight=1)
            group = ctk.CTkFrame(metadata, fg_color="transparent")
            group.grid(row=0, column=i, sticky="w", padx=14, pady=18)
            label(group, title, 11, color=T.MUTED).pack(anchor="w")
            label(group, value, 12, True, wraplength=170).pack(anchor="w", pady=4)
        items = section(left, f"Items ({len(sale['items'])})")
        item_table(items, sale["items"])
        payment = section(left, "Payment Information")
        key_values(payment, [("Payment Method", sale["payment"]), ("Amount Paid", T.money(sale["paid"])),
                             ("Change", T.money(sale["paid"] - sale["total"])), ("Amount Due", T.money(0)),
                             ("Payment Status", sale["status"]), ("Paid At", sale["date"].strftime("%d %b %Y, %I:%M %p"))])
        notes = section(left, "Notes")
        button(notes, "Edit", self.edit_notes, "edit", width=80).pack(anchor="e")
        label(notes, sale["notes"] or "-", color=T.MUTED, wraplength=550).pack(anchor="w", pady=8)
        label(right, "Receipt Preview", 17, True).pack(anchor="w", padx=20, pady=16)
        receipt = ctk.CTkFrame(right, fg_color="#FCFCFD", border_color=T.LINE, border_width=1, corner_radius=0)
        receipt.pack(fill="x", padx=18, pady=(0, 16))
        label(receipt, "MAIN STORE", 20, True, anchor="center").pack(fill="x", padx=18, pady=(22, 5))
        label(receipt, "123 Market Street, Makurdi\nBenue State, Nigeria\nTel: 0803 123 4567", 11,
              justify="center", anchor="center").pack(fill="x", padx=10, pady=(0, 15))
        receipt_body = ctk.CTkFrame(receipt, fg_color="transparent")
        receipt_body.pack(fill="x", padx=16)
        label(receipt_body, f"Receipt #: {sale_id}\nDate: {sale['date']:%d %b %Y, %I:%M %p}\nCashier: {sale['cashier']}\nPayment: {sale['payment']}",
              11, justify="left").pack(anchor="w", pady=(0, 10))
        ctk.CTkFrame(receipt_body, height=1, fg_color=T.MUTED).pack(fill="x", pady=5)
        for item in sale["items"]:
            row = ctk.CTkFrame(receipt_body, fg_color="transparent")
            row.pack(fill="x", pady=5)
            label(row, f"{item['name']} x{item['quantity']}", 10, wraplength=150).pack(side="left")
            label(row, T.money(item["price"] * item["quantity"]), 11).pack(side="right")
        key_values(receipt_body, [("Subtotal", T.money(sale["subtotal"])), ("Discount", T.money(sale["discount"]))])
        total = ctk.CTkFrame(receipt_body, fg_color="transparent")
        total.pack(fill="x", pady=12)
        label(total, "TOTAL", 18, True).pack(side="left")
        label(total, T.money(sale["total"]), 20, True).pack(side="right")
        label(receipt, "Thank you for shopping!\nGoods once sold are not returnable.", 11, anchor="center", justify="center").pack(fill="x", pady=(10, 20))
        # A human-readable receipt ID avoids pretending this is a scannable barcode.
        label(receipt, sale_id, 16, True, anchor="center").pack(fill="x", pady=(0, 20))
        button(right, "Print Receipt", self.print_receipt, "print", kind="primary").pack(fill="x", padx=18, pady=(0, 10))
        button(right, "Save as PDF", self.save_pdf, "save").pack(fill="x", padx=18, pady=(0, 18))

    def edit_notes(self):
        def save(value):
            self.sale["notes"] = value
            self.app.navigate("sale", sale_id=self.sale["id"])
        edit_text(self.app, "Sale Notes", self.sale["notes"], save)

    def print_receipt(self):
        self.app.toast("Receipt preview only. Printer integration is not connected yet.")

    def save_pdf(self):
        self.app.toast("PDF export is reserved for the next phase.")


class AuditDetails(Page):
    def __init__(self, app, log_id):
        super().__init__(app)
        self.log = next(log for log in self.store.logs if log["id"] == log_id)
        log = self.log
        header = self.heading("Audit Log Details", "View detailed information about this activity.",
                              ("Back to Audit Logs", lambda: app.navigate("audit")))
        button(header, "Export as PDF", lambda: app.toast("PDF export is reserved for the next phase."), "export", width=155).pack(side="right")
        banner = panel(self.body)
        banner.pack(fill="x", pady=(0, 16))
        banner_text = ctk.CTkFrame(banner, fg_color="transparent")
        banner_text.pack(side="left", padx=20, pady=16)
        label(banner_text, log["action"], 20, True).pack(anchor="w")
        label(banner_text, log["details"], 13, color=T.MUTED, wraplength=650).pack(anchor="w")
        label(banner, log["date"].strftime("%d %b %Y, %I:%M %p"), 17, True).pack(side="right", padx=22)
        columns = ctk.CTkFrame(self.body, fg_color="transparent")
        columns.pack(fill="x")
        columns.grid_columnconfigure(0, weight=1, uniform="audit")
        columns.grid_columnconfigure(1, weight=1, uniform="audit")
        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right = ctk.CTkFrame(columns, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        info = section(left, "Action Information")
        key_values(info, [("Action Type", log["action"]), ("Reference ID", log["id"]),
                          ("Date & Time", log["date"].strftime("%d %b %Y, %I:%M %p")),
                          ("User", log["user"]), ("IP/Device", log["device"]), ("Result", log["result"]), ("Duration", "0.3 seconds")])
        changes = section(left, "Changes Made")
        label(changes, log["details"], 13, color=T.MUTED, wraplength=440).pack(anchor="w", pady=10)
        related = section(right, "Related Data")
        if log["sale_id"]:
            sale = self.store.sale(log["sale_id"])
            button(related, "Sale Details", lambda: app.navigate("sale", sale_id=sale["id"]), "next", width=130).pack(anchor="e", pady=(0, 10))
            # Narrow audit columns use a compact summary to keep product names readable.
            for item in sale["items"]:
                row = ctk.CTkFrame(related, fg_color="transparent")
                row.pack(fill="x", pady=8)
                label(row, "", image=product_image(item["image"], 36)).pack(side="left", padx=(0, 10))
                label(row, f"{item['name']} x{item['quantity']}", 12).pack(side="left")
                label(row, T.money(item["price"] * item["quantity"]), 13, True).pack(side="right")
            key_values(related, [("Total Amount", T.money(sale["total"])), ("Payment Method", sale["payment"]), ("Payment Status", "Paid in full")])
            key_values(changes, [("Sale Number", sale["id"]), ("Total Items", str(len(sale["items"]))),
                                 ("Total Amount", T.money(sale["total"])), ("Payment Method", sale["payment"])])
        else:
            label(related, "No linked sale", 14, color=T.MUTED).pack(anchor="w", pady=12)
        previous = section(right, "Previous State")
        label(previous, "This action created a new record." if log["sale_id"] else "No previous state captured in this sample.",
              12, color=T.MUTED, wraplength=410).pack(anchor="w", pady=10)
        notes = section(right, "Notes")
        button(notes, "Edit", self.edit_notes, "edit", width=80).pack(anchor="e")
        label(notes, log["notes"] or "-", 13, color=T.MUTED, wraplength=410).pack(anchor="w", pady=8)

    def edit_notes(self):
        def save(value):
            self.log["notes"] = value
            self.app.navigate("log", log_id=self.log["id"])
        edit_text(self.app, "Audit Notes", self.log["notes"], save)
