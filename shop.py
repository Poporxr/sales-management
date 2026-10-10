"""Business logic for the shop app.

The UI calls these functions; they validate, talk to the database,
and write audit entries. Keeping the rules here (instead of scattered
across screens) means every screen behaves the same way, and the
supervisor can read one file to understand every rule.
"""

import math

import database

# Demo-only manager PIN. A real shop would store a hashed PIN per user
# and never keep it in the source code.
MANAGER_PIN = "1234"


def check_pin(entered):
    """True if the typed PIN matches. Demo gate, not real security."""
    return entered.strip() == MANAGER_PIN


def _clean_number(value, field):
    """Turn form text into a number, or explain what is wrong with it."""
    try:
        number = float(str(value).replace(",", "").strip() or 0)
    except ValueError:
        raise ValueError("Enter a valid %s." % field)
    if not math.isfinite(number) or number < 0:
        raise ValueError("%s cannot be negative." % field)
    return round(number, 2)


def _clean_whole(value, field):
    """Stock must be a whole number: you cannot sell half a bottle."""
    number = _clean_number(value, field)
    if number != int(number):
        raise ValueError("%s must be a whole number." % field)
    return int(number)


def validate_product(values, product_id=None):
    """Check product form values. Returns a cleaned dict, or raises
    ValueError with a message the UI can show directly to the user."""
    name = str(values.get("name", "")).strip()
    barcode = str(values.get("barcode", "")).strip()
    category = str(values.get("category", "")).strip()
    if not name:
        raise ValueError("Product name is required.")
    if not barcode:
        raise ValueError("Barcode is required.")
    if not category:
        raise ValueError("Category is required.")
    if len(name) > 60:
        raise ValueError("Keep the name under 60 characters.")
    # Barcodes must be unique, but the product being edited is allowed
    # to keep its own barcode.
    existing = database.get_product_by_barcode(barcode)
    if existing and existing["id"] != product_id:
        raise ValueError("Another product already uses this barcode.")
    return {
        "name": name,
        "barcode": barcode,
        "category": category,
        "price": _clean_number(values.get("price", 0), "Price"),
        "cost": _clean_number(values.get("cost", 0), "Cost"),
        "stock": _clean_whole(values.get("stock", 0), "Stock"),
        "brand": str(values.get("brand", "")).strip(),
        "unit": str(values.get("unit", "")).strip() or "Piece",
        # Image is just a filename in assets/products/. No validation
        # needed: an empty string simply means "no photo".
        "image": str(values.get("image", "")).strip(),
    }


def add_product(values, user):
    """Validate, save, and audit a new product."""
    clean = validate_product(values)
    product_id = database.add_product(**clean)
    database.log_action(user, "Product Added",
                        "%s | Barcode: %s" % (clean["name"], clean["barcode"]))
    return product_id


def update_product(product_id, values, user):
    """Validate, save, and audit a product edit."""
    clean = validate_product(values, product_id)
    old = database.get_product(product_id)
    database.update_product(product_id, **clean)
    database.log_action(user, "Product Edited",
                        "%s | Price: %s, Stock: %s" % (clean["name"], clean["price"], clean["stock"]))


def delete_product(product_id, user):
    """Delete a product and audit it. Past sales keep their snapshots,
    so old receipts are unaffected."""
    product = database.get_product(product_id)
    database.delete_product(product_id)
    database.log_action(user, "Product Deleted",
                        "%s | Barcode: %s" % (product["name"], product["barcode"]))


def adjust_stock(product_id, mode, quantity, reason, user):
    """Add, remove, or set stock, with a required reason.

    The reason is written into the audit log so anyone can later see
    why the stock number changed."""
    product = database.get_product(product_id)
    qty = _clean_whole(quantity, "Quantity")
    if not str(reason).strip():
        raise ValueError("A reason is required for every stock change.")
    if mode == "Add":
        new_stock = product["stock"] + qty
    elif mode == "Remove":
        new_stock = product["stock"] - qty
    else:  # Set
        new_stock = qty
    if new_stock < 0:
        raise ValueError("Stock cannot go below zero.")
    database.set_stock(product_id, new_stock)
    database.log_action(
        user, "Stock Adjusted",
        "%s | %s %d (%s) | %d -> %d"
        % (product["name"], mode, qty, reason.strip(), product["stock"], new_stock),
    )
    return new_stock


def cart_total(cart):
    """cart is {product_id: quantity}. Prices are read fresh from the
    database so a price edited mid-sale is charged correctly."""
    total = 0
    for product_id, qty in cart.items():
        product = database.get_product(product_id)
        total += product["price"] * qty
    return round(total, 2)


def checkout(cart, payment, paid, cashier, customer_name=""):
    """Run a complete sale. Raises ValueError with a user-friendly
    message if anything is wrong; the UI shows it and nothing is saved.

    On success returns the sale dict (with items attached). The receipt
    PDF is NOT generated here: it is built on demand when the user
    clicks Print, straight from the stored sale rows."""
    if not cart:
        raise ValueError("Add a product before completing the sale.")
    total = cart_total(cart)
    if payment == "Cash":
        try:
            paid = float(str(paid).replace(",", "").strip() or 0)
        except ValueError:
            raise ValueError("Enter a valid amount received.")
        if paid < total:
            raise ValueError("Amount received must cover the total.")
        change = round(paid - total, 2)
    else:  # Transfer: the exact total, no change involved.
        paid, change = total, 0
    # Build the item snapshots and check stock before writing anything.
    items = []
    for product_id, qty in cart.items():
        product = database.get_product(product_id)
        if product is None:
            raise ValueError("A product in the cart no longer exists.")
        if qty > product["stock"]:
            raise ValueError("Not enough stock for %s (only %d left)."
                             % (product["name"], product["stock"]))
        # Freeze the name and price now: if the product is renamed or
        # repriced tomorrow, this receipt still shows the truth.
        items.append({"product_id": product_id, "name": product["name"],
                      "price": product["price"], "quantity": qty})
    sale_id = database.record_sale(items, payment, paid, change, cashier,
                                   customer_name.strip())
    database.log_action(cashier, "Sale Completed",
                        "Receipt #%06d | %d items | %s"
                        % (sale_id, len(items), payment))
    sale = database.get_sale(sale_id)
    return sale
