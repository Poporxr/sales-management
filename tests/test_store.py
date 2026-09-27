import unittest
from services.mock_store import MockStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = MockStore()

    def test_cart_total_and_stock_limit(self):
        self.assertEqual(self.store.total, 5400)
        with self.assertRaises(ValueError):
            self.store.change_quantity(1, 25)
        self.assertEqual(self.store.cart[1], 2)
        self.store.change_quantity(1, -2)
        self.assertNotIn(1, self.store.cart)
        self.assertEqual(self.store.total, 4300)

    def test_checkout_validation(self):
        for amount in (0, 100, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.store.checkout("Cash", amount)
        self.assertEqual(len(self.store.sales), 48)
        self.assertTrue(self.store.cart)

    def test_checkout_snapshot_and_audit_link(self):
        sale = self.store.checkout("Cash", 6000)
        self.assertEqual(sale["total"], 5400)
        self.assertFalse(self.store.cart)
        self.assertEqual(self.store.logs[0]["sale_id"], sale["id"])
        self.store.product(1)["price"] = 999
        self.store.product(1)["name"] = "Renamed"
        self.assertEqual(sale["items"][0]["price"], 550)
        self.assertEqual(sale["items"][0]["name"], "Coca-Cola 50cl")

    def test_discount_recalculates_after_quantity_change(self):
        self.store.discount = 540
        self.store.change_quantity(5, -1)
        self.assertEqual(self.store.discount, 260)
        self.assertEqual(self.store.total, 2340)

    def test_stock_revalidated_at_checkout(self):
        self.store.product(1)["stock"] = 0
        with self.assertRaises(ValueError):
            self.store.checkout("Cash", 6000)


if __name__ == "__main__":
    unittest.main()
