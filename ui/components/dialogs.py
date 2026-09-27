"""Reusable modal shell and compact forms for the represented screen actions."""

import math
import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import label, button, entry, select


class Dialog(ctk.CTkToplevel):
    def __init__(self, app, title, width=470, height=360):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.configure(fg_color=T.WHITE)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda event: self.close())
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=26, pady=24)
        label(self.body, title, 23, True).pack(anchor="w", pady=(0, 16))
        self.after(60, self.activate)

    def activate(self):
        self.update_idletasks()
        x = self.app.winfo_rootx() + (self.app.winfo_width() - self.winfo_width()) // 2
        y = self.app.winfo_rooty() + (self.app.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()
        self.focus_force()

    def close(self):
        self.grab_release()
        self.destroy()


def confirm(app, title, message, action):
    dialog = Dialog(app, title, height=235)
    label(dialog.body, message, color=T.MUTED, wraplength=410).pack(anchor="w")
    actions = ctk.CTkFrame(dialog.body, fg_color="transparent")
    actions.pack(side="bottom", fill="x")
    button(actions, "Cancel", dialog.close, kind="neutral").pack(side="left")

    def accept():
        dialog.close()
        action()

    button(actions, "Confirm", accept, kind="danger").pack(side="right")
    return dialog


def edit_text(app, title, original, action):
    dialog = Dialog(app, title, height=320)
    field = ctk.CTkTextbox(dialog.body, height=135, fg_color=T.BG, text_color=T.INK, font=T.font())
    field.pack(fill="x")
    field.insert("1.0", original)

    def save():
        action(field.get("1.0", "end").strip())
        dialog.close()

    button(dialog.body, "Save Notes", save, "save", kind="primary").pack(anchor="e", pady=18)
    return dialog


def number_form(app, title, name, initial, action, integer=False):
    dialog = Dialog(app, title, height=285)
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
            action(int(value) if integer else round(value, 2))
            dialog.close()
        except ValueError:
            error.configure(text="Enter a non-negative " + ("whole number." if integer else "amount."))

    button(dialog.body, "Save Changes", save, "check", kind="primary").pack(anchor="e", pady=12)
    return dialog


class CheckoutDialog(Dialog):
    def __init__(self, app, on_complete):
        super().__init__(app, "Complete Sale", height=450)
        self.on_complete = on_complete
        label(self.body, "Total due", color=T.MUTED).pack(anchor="w")
        label(self.body, T.money(app.store.total), 34, True, T.BLUE).pack(anchor="w", pady=(0, 16))
        label(self.body, "Payment method", color=T.MUTED).pack(anchor="w")
        self.payment = select(self.body, ["Cash", "Transfer"], self.method_changed)
        self.payment.pack(fill="x", pady=(5, 12))
        label(self.body, "Amount received", color=T.MUTED).pack(anchor="w")
        self.amount = entry(self.body, "Amount received")
        self.amount.pack(fill="x", pady=5)
        self.amount.insert(0, str(app.store.total))
        self.error = label(self.body, "", 12, color=T.RED)
        self.error.pack(anchor="w", pady=5)
        button(self.body, "Complete Sale", self.complete, "check", kind="primary").pack(fill="x", pady=10)

    def method_changed(self, method):
        self.amount.configure(state="normal")
        self.amount.delete(0, "end")
        self.amount.insert(0, str(self.app.store.total))
        if method == "Transfer":
            self.amount.configure(state="disabled")

    def complete(self):
        try:
            amount = float(self.amount.get().replace(",", ""))
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("Enter a valid amount received.")
            sale = self.app.store.checkout(self.payment.get(), amount)
        except ValueError as error:
            self.error.configure(text=str(error) if "could not convert" not in str(error) else "Enter a valid amount received.")
            return
        self.close()
        self.on_complete(sale)
