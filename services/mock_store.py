"""Session-only sample data. No database, network, or filesystem writes."""

from copy import deepcopy
from datetime import datetime, timedelta
import math


PRODUCTS = [
    ("Coca-Cola 50cl", "5449000000996", "Beverages", 550, 400, 24, "Coca-Cola", "coke"),
    ("Pepsi 50cl", "5449000001234", "Beverages", 550, 400, 18, "Pepsi", "pepsi"),
    ("Fanta 50cl", "5449000005678", "Beverages", 550, 400, 20, "Fanta", "fanta"),
    ("Sprite 50cl", "5449000005679", "Beverages", 550, 400, 16, "Sprite", "sprite"),
    ("Peak Milk 400g", "6151100070041", "Groceries", 2800, 2500, 8, "Peak", "peak"),
    ("Indomie Chicken", "8964000100001", "Groceries", 300, 220, 45, "Indomie", "indomie"),
    ("Golden Morn 500g", "6154000011123", "Groceries", 1200, 900, 12, "Nestle", "golden"),
    ("Milo 200g", "6151000020045", "Groceries", 1500, 1150, 10, "Nestle", "milo"),
    ("Dettol Soap", "6192341100876", "Personal Care", 600, 450, 22, "Dettol", "dettol"),
    ("Closeup 120g", "6156000043210", "Personal Care", 850, 650, 9, "Closeup", "closeup"),
    ("Bread Loaf", "6157000054321", "Snacks", 700, 500, 14, "Fresh Bake", "bread"),
    ("Maggi Cubes", "6161000065432", "Groceries", 350, 250, 38, "Maggi", "maggi"),
]


class MockStore:
    """Own session state so widgets can change without losing the current sale.

    Revisions describe actual data edits, not mouse events or navigation. Pages
    use them to avoid rebuilding unchanged reports when the user comes back.
    """
    def __init__(self):
        self.products = [dict(id=i + 1, name=p[0], barcode=p[1], category=p[2],
                              price=p[3], cost=p[4], stock=p[5], brand=p[6],
                              image=p[7], minimum=10, unit="Piece")
                         for i, p in enumerate(PRODUCTS)]
        self.cart = {1: 2, 5: 1, 6: 3, 9: 1}
        self.cart_note = ""
        self.revision = 0
        self.product_revision = 0
        self.next_product_id = len(self.products) + 1
        self.held_cart = None
        self.discount = 0
        self.sales = []
        anchor = datetime(2025, 9, 26, 14, 28)
        for i in range(48):
            pairs = [(1, 2), (5, 1)] if i == 0 else [((i % 12) + 1, i % 4 + 1)]
            items = [dict(deepcopy(self.product(pid)), quantity=qty) for pid, qty in pairs]
            total = sum(p["price"] * p["quantity"] for p in items)
            self.sales.append(dict(id=f"{48-i:06d}", date=anchor - timedelta(hours=i * 3),
                                   items=items, total=total, subtotal=total, discount=0,
                                   payment="Transfer" if i % 4 == 2 else "Cash",
                                   status="Completed", cashier="Staff 1" if i % 6 == 4 else "Admin",
                                   paid=total, notes=""))
        self.logs = []
        actions = ["Sale Completed", "Product Updated", "Product Added", "Settings Changed",
                   "Sale Completed", "Product Deleted", "Sale Completed", "Product Updated", "User Login"]
        for i in range(124):
            action = actions[i % len(actions)]
            sale = self.sales[min(i, 47)]
            descriptions = {
                "Sale Completed": f"POS-20250926-{sale['id']} | {len(sale['items'])} items",
                "Product Updated": "Peak Milk 400g | Price changed from NGN 2,500 to NGN 2,800",
                "Product Added": "Milo 200g | Barcode: 6151000020045",
                "Settings Changed": 'Updated store name to "Main Store"',
                "Product Deleted": "Old Juice 50cl | Barcode: 5449000099999",
                "User Login": "Admin logged in",
            }
            self.logs.append(dict(id=f"{124-i:06d}", date=anchor - timedelta(hours=i * 2),
                                  user=sale["cashier"], action=action, details=descriptions[action],
                                  sale_id=sale["id"] if action == "Sale Completed" else None,
                                  notes="", result="Success", device="This Device"))

    def product(self, product_id):
        return next(p for p in self.products if p["id"] == product_id)

    def sale(self, sale_id):
        return next(s for s in self.sales if s["id"] == sale_id)

    @property
    def subtotal(self):
        return sum(self.product(pid)["price"] * qty for pid, qty in self.cart.items())

    @property
    def total(self):
        return self.subtotal - self.discount

    @property
    def discount(self):
        return round(self.subtotal * .1) if self._discount_enabled else 0

    @discount.setter
    def discount(self, amount):
        self._discount_enabled = amount > 0

    def change_quantity(self, product_id, delta):
        product = self.product(product_id)
        quantity = self.cart.get(product_id, 0) + delta
        if quantity > product["stock"]:
            raise ValueError("Only " + str(product["stock"]) + " available in stock.")
        if quantity <= 0:
            self.cart.pop(product_id, None)
        else:
            self.cart[product_id] = quantity
        if not self.cart:
            self.discount = 0
        elif self.discount:
            self.discount = round(self.subtotal * .1)

    @staticmethod
    def stock_status(product):
        if product["stock"] == 0:
            return "Out of Stock"
        return "Low Stock" if product["stock"] <= product["minimum"] else "In Stock"

    def record_action(self, action, details, before=None, after=None, product_id=None):
        """Keep before/after snapshots independent of later product edits."""
        self.logs.insert(0, dict(id=f"{max(int(x['id']) for x in self.logs)+1:06d}",
                                date=datetime.now(), user="Admin", action=action,
                                details=details, sale_id=None, product_id=product_id,
                                before=deepcopy(before), after=deepcopy(after),
                                notes="", result="Success", device="This Device"))
        self.revision += 1

    def validate_product(self, values, product_id=None):
        """Validate all fields before mutating state; failed forms change nothing."""
        result = dict(values)
        for field in ("name", "barcode", "category", "unit"):
            result[field] = str(result.get(field, "")).strip()
            if not result[field]:
                raise ValueError(f"{field.title()} is required.")
        if len(result["name"]) > 60 or len(result["barcode"]) > 32:
            raise ValueError("Use up to 60 characters for the name and 32 for the barcode.")
        if any(p["id"] != product_id and p["barcode"] == result["barcode"] for p in self.products):
            raise ValueError("Another product already uses this barcode.")
        for field in ("cost", "price", "stock", "minimum"):
            try:
                number = float(str(result.get(field, 0)).replace(",", ""))
            except ValueError:
                raise ValueError(f"Enter a valid {field}.") from None
            if not math.isfinite(number) or number < 0 or number > 99999999:
                raise ValueError(f"{field.title()} must be between 0 and 99,999,999.")
            if field in ("stock", "minimum") and not number.is_integer():
                raise ValueError(f"{field.title()} must be a whole number.")
            result[field] = int(number) if field in ("stock", "minimum") else round(number, 2)
        if product_id is not None and result["stock"] < self.reserved_quantity(product_id):
            raise ValueError("Stock cannot be lower than the quantity in an active or held sale.")
        return result

    def save_product(self, values, product_id=None):
        values = self.validate_product(values, product_id)
        before = deepcopy(self.product(product_id)) if product_id is not None else None
        if before is None:
            product = {"brand": "", "image": "", "description": "", **values}
            product["id"] = self.next_product_id
            self.next_product_id += 1
            self.products.append(product)
        else:
            product = self.product(product_id)
            for field in ("stock", "price"):
                if values[field] != product[field]:
                    product.setdefault(field + "_history", []).append(dict(
                        date=datetime.now(), old=product[field], new=values[field]))
            product.update(values)
        self.product_revision += 1
        action = "Product Added" if before is None else "Product Updated"
        if before and before["price"] != product["price"]:
            action = "Price Changed"
        self.record_action(action,
                           product["name"], before, product, product["id"])
        return product

    def reserved_quantity(self, product_id):
        held = self.held_cart["items"].get(product_id, 0) if self.held_cart else 0
        return max(self.cart.get(product_id, 0), held)

    def adjust_stock(self, product_id, mode, quantity, reason, notes=""):
        product = self.product(product_id)
        if quantity < 0 or int(quantity) != quantity or not reason.strip():
            raise ValueError("Enter a whole quantity and select a reason.")
        value = product["stock"] + quantity if mode == "Add Stock" else product["stock"] - quantity
        if mode == "Set Stock":
            value = quantity
        if value < self.reserved_quantity(product_id) or value < 0:
            raise ValueError("New stock cannot be negative or below an active/held sale quantity.")
        before = deepcopy(product)
        product.setdefault("stock_history", []).append(dict(date=datetime.now(), old=product["stock"], new=value))
        product["stock"] = value
        self.product_revision += 1
        self.record_action("Stock Adjusted", f"{product['name']} | {reason}", before, product, product_id)
        self.logs[0]["notes"] = notes

    def delete_product(self, product_id):
        product = self.product(product_id)
        self.cart.pop(product_id, None)
        if self.held_cart:
            self.held_cart["items"].pop(product_id, None)
        self.products.remove(product)
        self.product_revision += 1
        self.record_action("Product Deleted", product["name"], product, None, product_id)

    def hold_sale(self):
        # Swap whole sale drafts, including their notes and discount selection.
        current = dict(items=dict(self.cart), discount=self.discount, note=self.cart_note)
        if self.held_cart:
            held = self.held_cart
            self.cart, self.cart_note = held["items"], held["note"]
            self.discount = held["discount"]
            self.held_cart = current if current["items"] else None
        elif self.cart:
            self.held_cart = current
            self.cart, self.cart_note = {}, ""
            self.discount = 0

    def checkout(self, payment, paid):
        if not self.cart:
            raise ValueError("Add a product before completing the sale.")
        if not math.isfinite(paid) or paid < self.total:
            raise ValueError("Amount received must cover the total.")
        for pid, quantity in self.cart.items():
            if quantity > self.product(pid)["stock"]:
                raise ValueError(f"Not enough stock for {self.product(pid)['name']}.")
        items = [dict(deepcopy(self.product(pid)), quantity=qty) for pid, qty in self.cart.items()]
        sale_id = f"{max(int(s['id']) for s in self.sales) + 1:06d}"
        sale = dict(id=sale_id, date=datetime.now(), items=items, subtotal=self.subtotal,
                    discount=self.discount, total=self.total, payment=payment,
                    paid=paid, status="Completed", cashier="Admin", notes=self.cart_note)
        self.sales.insert(0, sale)
        self.logs.insert(0, dict(id=f"{max(int(x['id']) for x in self.logs)+1:06d}",
                                date=sale["date"], user="Admin", action="Sale Completed",
                                details=f"POS-{sale['date']:%Y%m%d}-{sale_id} | {len(items)} items",
                                sale_id=sale_id, notes="", result="Success", device="This Device"))
        self.cart.clear()
        self.cart_note = ""
        self.discount = 0
        self.revision += 1
        return sale
