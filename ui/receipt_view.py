"""Receipt preview: shows the receipt inside the app after checkout.

It looks like a thermal printer slip (narrow, monospace, centered
header) but it is just labels on screen: nothing is saved to disk.
The Print button generates the real PDF on demand and opens it in
the system's PDF viewer.
"""

from tkinter import messagebox

import customtkinter as ctk

import receipt
from ui import theme as T
from ui.widgets import label, button

MONO = "Courier New"


def _money(amount):
    amount = round(float(amount), 2)
    if amount == int(amount):
        return "\u20a6{:,.0f}".format(amount)
    return "\u20a6{:,.2f}".format(amount)


class ReceiptPreview(ctk.CTkToplevel):
    """A thermal-slip look built from labels. Takes a sale dict (with
    items) as returned by shop.checkout()."""

    def __init__(self, parent, sale, config):
        super().__init__(parent)
        self.sale = sale
        self.config = config
        self.title("Receipt #%06d" % sale["id"])
        self.geometry("360x640")
        self.transient(parent)
        self.grab_set()  # modal: the sale screen waits for this dialog

        # Gray backdrop so the white slip stands out like paper.
        backdrop = ctk.CTkFrame(self, fg_color=T.BG, corner_radius=0)
        backdrop.pack(fill="both", expand=True, padx=16, pady=16)

        slip = ctk.CTkScrollableFrame(backdrop, fg_color=T.WHITE, width=300)
        slip.pack(fill="both", expand=True, padx=10, pady=10)

        def line(text="", bold=False, size=10, align="center"):
            # align is center/left/right; anchor must match for CTkLabel.
            anchors = {"center": "center", "left": "w", "right": "e"}
            label(slip, text, size, bold, T.INK, font=(MONO, size, "bold" if bold else "normal"),
                  anchor=anchors[align]).pack(fill="x", padx=8)

        def divider():
            line("- " * 19, size=8)

        # Header: who sold it.
        line(config.get("store_name", "Store"), bold=True, size=13)
        line(config.get("address", ""), size=8)
        line(config.get("phone", ""), size=8)
        divider()

        # Meta.
        line("Date: %s" % sale["date"], size=8, align="left")
        line("Receipt: #%06d" % sale["id"], size=8, align="left")
        line("Cashier: %s" % sale["cashier"], size=8, align="left")
        if sale["customer_name"]:
            line("Customer: %s" % sale["customer_name"], size=8, align="left")
        divider()

        # Items.
        for item in sale["items"]:
            line(item["name"][:30], size=9, align="left")
            line("  %d x %s = %s" % (item["quantity"], _money(item["price"]),
                                     _money(item["price"] * item["quantity"])),
                 size=8, align="right")
        divider()

        # Totals.
        line("TOTAL: %s" % _money(sale["total"]), bold=True, size=12, align="right")
        line("Paid (%s): %s" % (sale["payment"], _money(sale["paid"])),
             size=9, align="right")
        if sale["payment"] == "Cash":
            line("Change: %s" % _money(sale["change"]), size=9, align="right")
        divider()

        line(config.get("receipt_footer", "Thank you!"), size=8)
        line("", size=8)  # breathing room at the bottom of the slip

        # Actions.
        actions = ctk.CTkFrame(backdrop, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 10))
        button(actions, "Print", self.print_receipt).pack(side="left", expand=True,
                                                         fill="x", padx=(0, 6))
        button(actions, "Close", self.destroy, kind="secondary").pack(
            side="left", expand=True, fill="x")

    def print_receipt(self):
        """Generate the PDF now and open it. This is the ONLY place a
        receipt file is ever created."""
        try:
            path = receipt.generate_receipt(self.sale["id"], self.config)
        except Exception as e:
            messagebox.showerror("Print failed",
                                 "Could not build the receipt:\n%s" % e)
            return
        if not receipt.open_file(path):
            messagebox.showwarning(
                "No viewer found",
                "The receipt was saved to:\n%s\n\nOpen it manually to print."
                % path)
