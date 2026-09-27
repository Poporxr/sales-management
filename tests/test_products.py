"""State boundaries that the new forms and cached pages depend on."""

from copy import deepcopy
import unittest
from services.mock_store import MockStore


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.store = MockStore()
        self.values = dict(name="Test Product", barcode="LOCAL-001", category="Others",
                           unit="Piece", price=100, cost=60, stock=12, minimum=4,
                           image="", description="Local sample")

    def test_add_is_validated_and_ids_never_reused(self):
        first = self.store.save_product(self.values)
        with self.assertRaises(ValueError):
            self.store.save_product(self.values)
        self.store.delete_product(first["id"])
        second = self.store.save_product(self.values)
        self.assertGreater(second["id"], first["id"])
        self.assertEqual(self.store.logs[0]["action"], "Product Added")

    def test_invalid_form_has_no_partial_effect(self):
        before = deepcopy(self.store.products)
        for changes in ({"stock": -1}, {"price": "nan"}, {"stock": 1.5}, {"barcode": ""}):
            with self.assertRaises(ValueError):
                self.store.save_product({**self.values, **changes})
        self.assertEqual(self.store.products, before)
        self.assertEqual(self.store.revision, 0)

    def test_stock_modes_and_reason_snapshots(self):
        self.store.adjust_stock(1, "Add Stock", 12, "Restock from supplier", "Delivery")
        self.assertEqual(self.store.product(1)["stock"], 36)
        self.assertEqual(self.store.logs[0]["before"]["stock"], 24)
        self.store.adjust_stock(1, "Remove Stock", 3, "Damaged")
        self.assertEqual(self.store.product(1)["stock"], 33)
        self.store.adjust_stock(1, "Set Stock", 20, "Stock count correction")
        self.assertEqual(self.store.product(1)["stock"], 20)
        with self.assertRaises(ValueError):
            self.store.adjust_stock(1, "Remove Stock", 50, "Damaged")

    def test_held_items_block_stock_reduction_and_keep_notes(self):
        self.store.cart_note = "Pickup at 4 PM"
        self.store.discount = 540
        self.store.hold_sale()
        with self.assertRaises(ValueError):
            self.store.adjust_stock(1, "Set Stock", 1, "Stock count correction")
        self.store.hold_sale()
        self.assertEqual(self.store.cart_note, "Pickup at 4 PM")
        self.assertEqual(self.store.discount, 540)

    def test_price_edit_changes_revision_without_mutating_receipts(self):
        old_sale = deepcopy(self.store.sales[0])
        values = {**self.store.product(1), "price": 650}
        self.store.save_product(values, 1)
        self.assertEqual(self.store.product_revision, 1)
        self.assertEqual(self.store.logs[0]["action"], "Price Changed")
        self.assertEqual(self.store.logs[0]["before"]["price"], 550)
        self.assertEqual(self.store.sales[0], old_sale)


if __name__ == "__main__":
    unittest.main()
