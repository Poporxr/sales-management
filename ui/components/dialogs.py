"""Desktop modal lifecycle, payment review, and one-action mock authorization.

Forms keep their fields when validation fails. Nested authorization restores the
original form's mouse/keyboard grab when it closes, including on cancellation.
"""

import math
import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import (label, button, entry, icon_button, icon,
                                   ScrollArea, Table, key_values)


class Dialog(ctk.CTkToplevel):
    # This app uses the native light title bar. CTk's optional Windows recoloring
    # hides/re-shows a window and races with modal activation, causing flashes.
    _deactivate_windows_window_header_manipulation = True

    def __init__(self, app, title, width=470, height=360, subtitle="", symbol="box"):
        super().__init__(app)
        self.withdraw()
        self.app, self.previous_grab = app, app.grab_current()
        self.title(title)
        self.configure(fg_color=T.WHITE)
        scale = self._get_window_scaling()
        width = min(width, int(app.winfo_width() / scale) - 30)
        height = min(height, int(app.winfo_height() / scale) - 24)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(self.previous_grab if isinstance(self.previous_grab, ctk.CTkToplevel) else app)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda event: self.close())

        # Keep heading/actions outside the scrolling form so they are reachable
        # even on Windows displays with larger text scaling.
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 12))
        label(header, "", image=icon(symbol, T.BLUE, 26)).pack(side="left", padx=(0, 12))
        text = ctk.CTkFrame(header, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        label(text, title, 21, True).pack(anchor="w")
        if subtitle:
            label(text, subtitle, 12, color=T.MUTED, wraplength=width-110, justify="left").pack(anchor="w")
        self.close_button = icon_button(header, "close", self.close, "Close dialog", "neutral", 22)
        self.close_button.pack(side="right", anchor="n")
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(side="bottom", fill="x", padx=22, pady=14)
        self.body = ScrollArea(self)
        self.body.pack(fill="both", expand=True, padx=22)
        x = app.winfo_rootx() + max(0, (app.winfo_width() - int(width * scale)) // 2)
        y = app.winfo_rooty() + max(0, (app.winfo_height() - int(height * scale)) // 2)
        self.geometry(f"+{x}+{y}")
        self.activation_job = self.after(20, self.activate)

    def activate(self):
        self.activation_job = None
        self.deiconify()
        self.grab_set()
        self.focus_set()

    def close(self):
        if self.activation_job:
            self.after_cancel(self.activation_job)
        self.grab_release()
        previous = self.previous_grab
        self.destroy()
        if previous and previous.winfo_exists():
            previous.grab_set()

    def actions(self, text, action, symbol="check", kind="primary"):
        button(self.footer, text, action, symbol, kind=kind, width=150).pack(side="right")
        button(self.footer, "Cancel", self.close, kind="neutral", width=100).pack(side="right", padx=10)


def confirm(app, title, message, action):
    dialog = Dialog(app, title, height=225, symbol="info")
    label(dialog.body, message, color=T.MUTED, wraplength=390, justify="left").pack(anchor="w", pady=10)
    def accept():
        dialog.close()
        action()
    dialog.actions("Confirm", accept, kind="danger")
    return dialog


def edit_text(app, title, original, action):
    dialog = Dialog(app, title, height=320, symbol="edit")
    field = ctk.CTkTextbox(dialog.body, height=130, fg_color=T.BG, text_color=T.INK, font=T.font())
    field.pack(fill="x")
    field.insert("1.0", original)
    def save():
        action(field.get("1.0", "end").strip())
        dialog.close()
    dialog.actions("Save Notes", save, "save")
    return dialog


class ManagerDialog(Dialog):
    """A mock PIN authorizes exactly the supplied callback, never a whole session."""
    def __init__(self, app, action, description="This action requires manager authorization."):
        super().__init__(app, "Manager Authorization", width=490, height=350,
                         subtitle="Enter your manager PIN to continue.", symbol="shield")
        self.action = action
        label(self.body, description, 13, color=T.MUTED, fg_color=T.BLUE_LIGHT,
              corner_radius=6, wraplength=400, justify="left", padx=14, pady=14).pack(fill="x", pady=(0, 18))
        label(self.body, "Manager PIN", 13, True).pack(anchor="w")
        self.pin = entry(self.body, "")
        self.pin.configure(show="*", justify="center")
        self.pin.pack(fill="x", pady=8)
        self.pin.bind("<Return>", lambda event: self.authorize())
        self.error = label(self.body, "", 12, color=T.RED)
        self.error.pack(anchor="w")
        self.actions("Authorize", self.authorize, "lock")

    def authorize(self):
        if self.pin.get() != "1234":
            self.error.configure(text="Incorrect manager PIN.")
            self.pin.delete(0, "end")
            self.pin.focus_set()
            return
        self.close()
        self.action()


def number_form(app, title, name, initial, action, integer=False):
    dialog = Dialog(app, title, height=285, symbol="edit")
    label(dialog.body, name, color=T.MUTED).pack(anchor="w")
    field = entry(dialog.body, "0")
    field.pack(fill="x", pady=8)
    field.insert(0, str(initial))
    error = label(dialog.body, "", 12, color=T.RED)
    error.pack(anchor="w")
    def save():
        try:
            value = float(field.get().replace(",", ""))
            if not math.isfinite(value) or value < 0 or (integer and not value.is_integer()):
                raise ValueError
        except ValueError:
            error.configure(text="Enter a valid non-negative number.")
            return
        def apply():
            try:
                action(int(value) if integer else round(value, 2))
                dialog.close()
            except ValueError as exception:
                error.configure(text=str(exception))
        ManagerDialog(app, apply, "Changing product prices requires manager approval.")
    dialog.actions("Save Changes", save, "save")
    return dialog


class CheckoutDialog(Dialog):
    def __init__(self, app, on_complete):
        super().__init__(app, "Complete Sale", width=870, height=610,
                         subtitle="Review the items and enter payment details.", symbol="cart")
        self.on_complete = on_complete
        self.submitting = False
        columns = ctk.CTkFrame(self.body, fg_color="transparent")
        columns.pack(fill="x")
        columns.grid_columnconfigure(0, weight=3, uniform="checkout")
        columns.grid_columnconfigure(1, weight=2, uniform="checkout")
        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        right = ctk.CTkFrame(columns, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        top = ctk.CTkFrame(left, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        label(top, f"Sale Items ({len(app.store.cart)})", 16, True).pack(side="left")
        button(top, "Edit Cart", self.close, "edit", width=95, height=28).pack(side="right")
        table = Table(left, ["Product", "Unit Price", "Qty", "Total"], [4, 2, 1, 2])
        table.pack(fill="x")
        for pid, quantity in app.store.cart.items():
            product = app.store.product(pid)
            table.add([lambda p, item=product: label(p, item["name"], 12, wraplength=140, justify="left"),
                       T.money(product["price"]), quantity, T.money(product["price"] * quantity)])
        key_values(left, [("Subtotal", T.money(app.store.subtotal)), ("Discount", T.money(app.store.discount)),
                          ("Total Amount", T.money(app.store.total))])
        label(right, "Payment Details", 16, True).pack(anchor="w", pady=(0, 16))
        label(right, "Payment Method", color=T.MUTED).pack(anchor="w")
        self.payment = ctk.CTkSegmentedButton(right, values=["Cash", "Transfer"], command=self.method_changed,
                                             height=36, font=T.font(13), selected_color=T.BLUE)
        self.payment.pack(fill="x", pady=(5, 16))
        self.payment.set("Cash")
        label(right, "Amount Received", color=T.MUTED).pack(anchor="w")
        self.amount = entry(right, "Amount received")
        self.amount.pack(fill="x", pady=(5, 12))
        self.amount.insert(0, str(app.store.total))
        self.amount.bind("<KeyRelease>", lambda event: self.update_change())
        label(right, "Change", color=T.MUTED).pack(anchor="w")
        self.change_label = label(right, T.money(0), 25, True, T.GREEN,
                                  fg_color=T.GREEN_LIGHT, corner_radius=6, padx=12, height=54)
        self.change_label.pack(fill="x", pady=6)
        self.error = label(right, "", 12, color=T.RED, wraplength=265, justify="left")
        self.error.pack(anchor="w", pady=8)
        self.actions("Complete Sale", self.complete)

    def method_changed(self, method):
        self.amount.configure(state="normal")
        self.amount.delete(0, "end")
        self.amount.insert(0, str(self.app.store.total))
        if method == "Transfer":
            self.amount.configure(state="disabled")
        self.update_change()

    def update_change(self):
        try:
            amount = float(self.amount.get().replace(",", ""))
            if not math.isfinite(amount):
                raise ValueError
            change = amount - self.app.store.total
            self.change_label.configure(text=T.money(max(0, change)))
            self.error.configure(text=f"Amount due: {T.money(-change)}" if change < 0 else "")
        except ValueError:
            self.change_label.configure(text="-")
            self.error.configure(text="Enter a valid amount received.")

    def complete(self):
        # Guard against a double click while the success dialog is being opened.
        if self.submitting:
            return
        try:
            amount = float(self.amount.get().replace(",", ""))
            sale = self.app.store.checkout(self.payment.get(), amount)
        except ValueError as error:
            self.error.configure(text=str(error) if "could not convert" not in str(error) else "Enter a valid amount received.")
            return
        self.submitting = True
        self.close()
        self.on_complete(sale)


class SaleCompletedDialog(Dialog):
    def __init__(self, app, sale):
        super().__init__(app, "Sale Completed!", width=710, height=625,
                         subtitle="The sale has been recorded for this session.", symbol="check")
        columns = ctk.CTkFrame(self.body, fg_color="transparent")
        columns.pack(fill="x")
        columns.grid_columnconfigure((0, 1), weight=1, uniform="summary")
        receipt = ctk.CTkFrame(columns, fg_color=T.BG, corner_radius=6)
        receipt.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        label(receipt, "MAIN STORE", 19, True, anchor="center").pack(fill="x", pady=15)
        label(receipt, f"Receipt #{sale['id']}\n{sale['date']:%d %b %Y, %I:%M %p}\nCashier: {sale['cashier']}",
              11, justify="left").pack(anchor="w", padx=14, pady=(0, 12))
        for item in sale["items"]:
            label(receipt, f"{item['name']} x{item['quantity']}\n{T.money(item['price'] * item['quantity'])}",
                  12, wraplength=230, justify="left").pack(anchor="w", padx=14, pady=5)
        label(receipt, f"TOTAL  {T.money(sale['total'])}", 19, True).pack(anchor="w", padx=14, pady=15)
        label(receipt, "Thank you for shopping!", 12).pack(anchor="w", padx=14, pady=(0, 15))
        summary = ctk.CTkFrame(columns, fg_color="transparent")
        summary.grid(row=0, column=1, sticky="nsew")
        label(summary, "Sale Summary", 16, True).pack(anchor="w")
        key_values(summary, [("Sale Number", sale["id"]), ("Total Items", len(sale["items"])),
                             ("Total Amount", T.money(sale["total"])), ("Payment", sale["payment"]),
                             ("Amount Received", T.money(sale["paid"])),
                             ("Change", T.money(sale["paid"] - sale["total"])), ("Cashier", sale["cashier"])])
        button(summary, "Print Receipt", lambda: app.toast("Printer integration is not connected yet."), "print").pack(fill="x", pady=(12, 5))
        button(summary, "View Receipt", lambda: self.go("sale", sale_id=sale["id"]), "receipt").pack(fill="x", pady=5)
        email = button(summary, "Send via Email", lambda: None, "mail", kind="neutral")
        email.configure(state="disabled")
        email.pack(fill="x", pady=5)
        button(self.footer, "Back to Home", lambda: self.go("home"), "home", kind="primary").pack(side="right")
        button(self.footer, "New Sale", self.close, "cart").pack(side="right", padx=10)

    def go(self, route, **params):
        self.close()
        self.app.navigate(route, **params)
