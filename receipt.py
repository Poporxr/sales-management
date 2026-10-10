"""Thermal-style receipt PDFs, 80mm wide like a real shop printer slip.

Small and minimal on purpose: store header, items, totals, footer.
Receipts are generated ON DEMAND only, when the user clicks Print.
The database rows are the permanent record; any receipt can be
regenerated from them at any time, so no PDF is ever stored.

generate_receipt(sale_id, config) builds the PDF in the system temp
folder and returns its path. open_file(path) opens it in the default
PDF viewer, where the user can save or print it.
"""

import os
import subprocess
import sys
import tempfile
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

import database

# A thermal printer slip is 80mm wide. The height just needs to be tall
# enough; fpdf clips nothing because we never write past it.
PAGE_WIDTH, PAGE_HEIGHT = 80, 200


def _line(pdf, text="", bold=False, size=9, align="L"):
    """One line of text on the receipt, then move to the next line."""
    pdf.set_font("Courier", "B" if bold else "", size)
    pdf.cell(w=0, h=4.5, text=text, align=align,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _divider(pdf):
    """A dashed line, the way thermal printers separate sections."""
    _line(pdf, "-" * 38, size=8, align="C")


def generate_receipt(sale_id, config):
    """Build the PDF for a sale and return where it was saved.

    The file goes to the system temp folder: it is a printout, not
    data. The viewer lets the user save or print it from there."""
    sale = database.get_sale(sale_id)
    if sale is None:
        raise ValueError("Sale not found.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "receipt_%06d_%s.pdf" % (sale_id, stamp)
    path = os.path.join(tempfile.gettempdir(), filename)

    pdf = FPDF(orientation="P", unit="mm", format=(PAGE_WIDTH, PAGE_HEIGHT))
    pdf.set_margins(4, 4, 4)  # narrow margins: slips are tiny already
    pdf.add_page()

    # Header: who sold it.
    _line(pdf, config.get("store_name", "Store"), bold=True, size=12, align="C")
    _line(pdf, config.get("address", ""), size=8, align="C")
    _line(pdf, config.get("phone", ""), size=8, align="C")
    _divider(pdf)

    # Meta: when, which receipt, who served, who bought.
    _line(pdf, "Date: %s" % sale["date"], size=8)
    _line(pdf, "Receipt: #%06d" % sale["id"], size=8)
    _line(pdf, "Cashier: %s" % sale["cashier"], size=8)
    if sale["customer_name"]:
        # Only printed when the cashier actually typed a name.
        _line(pdf, "Customer: %s" % sale["customer_name"], size=8)
    _divider(pdf)

    # Items: name on one line, qty x price on the next, keeps it narrow.
    for item in sale["items"]:
        _line(pdf, item["name"][:32], size=9)
        _line(pdf, "  %d x %s = %s" % (
            item["quantity"],
            _money(item["price"]),
            _money(item["price"] * item["quantity"])), size=8, align="R")
    _divider(pdf)

    # Totals.
    _line(pdf, "TOTAL: %s" % _money(sale["total"]), bold=True, size=11, align="R")
    _line(pdf, "Paid (%s): %s" % (sale["payment"], _money(sale["paid"])), size=9, align="R")
    if sale["payment"] == "Cash":
        _line(pdf, "Change: %s" % _money(sale["change"]), size=9, align="R")
    _divider(pdf)

    # Footer: configurable goodbye line from store.json.
    _line(pdf, config.get("receipt_footer", "Thank you!"), size=8, align="C")

    pdf.output(path)
    return path


def open_file(path):
    """Open a file in the system's default viewer.

    Returns True on success, False if no viewer could be launched.
    Never raises: a missing PDF viewer must not crash the shop app."""
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: the Windows way to open a file
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
        return True
    except Exception:
        return False


def _money(amount):
    """Naira formatting for the receipt. Kept here so receipt.py does
    not depend on the UI theme module.

    Uses NGN instead of the naira sign: the built-in PDF fonts cannot
    render the glyph, and this way the receipt needs no font files."""
    amount = round(float(amount), 2)
    if amount == int(amount):
        return "NGN {:,.0f}".format(amount)
    return "NGN {:,.2f}".format(amount)
