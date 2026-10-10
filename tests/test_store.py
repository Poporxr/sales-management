"""Unit tests for the shop's business rules.

Run from the project root:  python -m unittest discover -s tests

The tests use a temporary database file, so the real shop.db is never
touched. database.DB_PATH is read fresh on every connection, which is
exactly why the tests can swap it out.
"""

import os
import sys
import tempfile
import unittest

# Import the project root so `import database` works from the tests folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import shop
import receipt


class ShopTest(unittest.TestCase):
    def setUp(self):
        """Fresh empty database for every test."""
        self.tmp = tempfile.TemporaryDirectory()
        database.DB_PATH = os.path.join(self.tmp.name, "test.db")
        database.init_db()
        database.add_product("Coke 50cl", "111", "Beverages",
                             price=500, cost=350, stock=10, brand="Coke")
        database.add_product("Pepsi 50cl", "222", "Beverages",
                             price=500, cost=350, stock=5, brand="Pepsi")
        self.config = {"store_name": "Test Store", "address": "Test Rd",
                       "phone": "000", "receipt_footer": "Thanks"}

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------ checkout ---

    def test_checkout_deducts_stock(self):
        """The original prototype never deducted stock; this must."""
        coke = database.get_product_by_barcode("111")
        sale = shop.checkout({coke["id"]: 3}, "Cash", 2000, "Admin")
        after = database.get_product(coke["id"])
        self.assertEqual(after["stock"], 7)
        self.assertEqual(sale["total"], 1500)
        self.assertEqual(sale["change"], 500)

    def test_checkout_fails_on_insufficient_stock(self):
        """Selling more than the shelf holds is refused, and nothing
        is written: no sale, no stock change."""
        pepsi = database.get_product_by_barcode("222")
        with self.assertRaises(ValueError):
            shop.checkout({pepsi["id"]: 99}, "Cash", 99999, "Admin")
        self.assertEqual(len(database.list_sales()), 0)
        self.assertEqual(database.get_product(pepsi["id"])["stock"], 5)

    def test_checkout_rejects_short_payment(self):
        coke = database.get_product_by_barcode("111")
        with self.assertRaises(ValueError):
            shop.checkout({coke["id"]: 2}, "Cash", 500, "Admin")
        self.assertEqual(len(database.list_sales()), 0)

    def test_transfer_uses_exact_total(self):
        coke = database.get_product_by_barcode("111")
        sale = shop.checkout({coke["id"]: 2}, "Transfer", 0, "Admin")
        self.assertEqual(sale["paid"], 1000)
        self.assertEqual(sale["change"], 0)

    def test_sale_freezes_price_snapshot(self):
        """If the price changes later, the old sale still shows the
        price that was actually charged."""
        coke = database.get_product_by_barcode("111")
        shop.checkout({coke["id"]: 1}, "Cash", 500, "Admin")
        database.update_product(coke["id"], "Coke 50cl", "111", "Beverages",
                                999, 350, 9, "Coke", "Piece")
        sale = database.get_sale(1)
        self.assertEqual(sale["items"][0]["price"], 500)

    # ---------------------------------------------------- validation ---

    def test_validation_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            shop.validate_product({"name": "", "barcode": "333",
                                   "category": "Beverages", "price": 100})

    def test_validation_rejects_duplicate_barcode(self):
        with self.assertRaises(ValueError):
            shop.validate_product({"name": "New Drink", "barcode": "111",
                                   "category": "Beverages", "price": 100})

    def test_validation_rejects_negative_price(self):
        with self.assertRaises(ValueError):
            shop.validate_product({"name": "New Drink", "barcode": "333",
                                   "category": "Beverages", "price": -50})

    def test_validation_rejects_fractional_stock(self):
        with self.assertRaises(ValueError):
            shop.validate_product({"name": "New Drink", "barcode": "333",
                                   "category": "Beverages", "price": 100,
                                   "stock": 2.5})

    def test_edit_keeps_own_barcode(self):
        """Editing a product without touching its barcode must not
        trip the duplicate-barcode check."""
        coke = database.get_product_by_barcode("111")
        clean = shop.validate_product({"name": "Coke 50cl", "barcode": "111",
                                       "category": "Beverages", "price": 550},
                                      product_id=coke["id"])
        self.assertEqual(clean["price"], 550)

    # --------------------------------------------------------- pin ---

    def test_pin_gate(self):
        self.assertTrue(shop.check_pin("1234"))
        self.assertFalse(shop.check_pin("0000"))
        self.assertFalse(shop.check_pin(""))

    # ------------------------------------------------------- audit ---

    def test_audit_entry_written_on_product_add(self):
        shop.add_product({"name": "Milo", "barcode": "444",
                          "category": "Groceries", "price": 1500}, "Admin")
        entries = database.list_audit()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "Product Added")
        self.assertEqual(entries[0]["user"], "Admin")

    def test_audit_entry_written_on_sale(self):
        coke = database.get_product_by_barcode("111")
        shop.checkout({coke["id"]: 1}, "Cash", 500, "Cashier 1")
        actions = [e["action"] for e in database.list_audit()]
        self.assertIn("Sale Completed", actions)

    def test_stock_adjust_requires_reason(self):
        coke = database.get_product_by_barcode("111")
        with self.assertRaises(ValueError):
            shop.adjust_stock(coke["id"], "Add", 5, "", "Admin")
        shop.adjust_stock(coke["id"], "Add", 5, "delivery", "Admin")
        self.assertEqual(database.get_product(coke["id"])["stock"], 15)

    # ----------------------------------------------------- receipt ---

    def test_receipt_pdf_created_on_demand(self):
        """The PDF is only built when asked: generate it and check the
        file exists and is a real PDF."""
        coke = database.get_product_by_barcode("111")
        sale = shop.checkout({coke["id"]: 2}, "Cash", 1500, "Admin",
                             customer_name="Ada")
        path = receipt.generate_receipt(sale["id"], self.config)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)
        with open(path, "rb") as f:
            self.assertEqual(f.read(4), b"%PDF")


if __name__ == "__main__":
    unittest.main()
