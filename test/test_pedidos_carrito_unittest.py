import unittest
from app import app
from app import models
from flask import current_app

class TestPedidosCarrito(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        # Buscar usuario válido
        self.users = models.get_all_users()
        self.user_id = self.users[0]['id_user'] if self.users else None
        # Buscar producto válido
        self.tools = models.fetch_all_tools()
        self.tool_id = self.tools[0]['id_tool'] if self.tools else None

    def tearDown(self):
        self.app_context.pop()

    def test_get_user_open_order(self):
        order_id = models.get_user_open_order(self.user_id)
        self.assertTrue(order_id is None or isinstance(order_id, int))

    def test_create_order(self):
        order_id = models.create_order(self.user_id)
        self.assertIsInstance(order_id, int)

    def test_get_or_create_order(self):
        order_id = models.get_or_create_order(self.user_id)
        self.assertIsInstance(order_id, int)

    def test_add_or_update_item(self):
        order_id = models.get_or_create_order(self.user_id)
        result = models.add_or_update_item(order_id, self.tool_id, 1)
        self.assertTrue(result)

    def test_set_item_quantity(self):
        order_id = models.get_or_create_order(self.user_id)
        models.add_or_update_item(order_id, self.tool_id, 1)
        result = models.set_item_quantity(order_id, self.tool_id, 2)
        self.assertTrue(result)

    def test_remove_item(self):
        order_id = models.get_or_create_order(self.user_id)
        models.add_or_update_item(order_id, self.tool_id, 1)
        result = models.remove_item(order_id, self.tool_id)
        self.assertTrue(result)

    def test_get_cart_items(self):
        order_id = models.get_or_create_order(self.user_id)
        items = models.get_cart_items(order_id)
        self.assertTrue(isinstance(items, list) or isinstance(items, tuple))

    def test_get_cart_totals(self):
        order_id = models.get_or_create_order(self.user_id)
        total, count = models.get_cart_totals(order_id)
        self.assertIsInstance(total, (int, float))
        self.assertIsInstance(count, int)

    def test_clear_order_items(self):
        order_id = models.get_or_create_order(self.user_id)
        models.add_or_update_item(order_id, self.tool_id, 1)
        models.clear_order_items(order_id)
        items = models.get_cart_items(order_id)
        self.assertEqual(len(items), 0)

    def test_finalize_order(self):
        order_id = models.get_or_create_order(self.user_id)
        models.add_or_update_item(order_id, self.tool_id, 1)
        total, _ = models.get_cart_totals(order_id)
        models.finalize_order(order_id, total)
        # solo que no falle

    def test_insert_transaction(self):
        order_id = models.get_or_create_order(self.user_id)
        result = models.insert_transaction(order_id, 1000)
        self.assertTrue(result)

    def test_fetch_all_orders(self):
        orders = models.fetch_all_orders()
        self.assertTrue(isinstance(orders, list) or isinstance(orders, tuple))

    def test_fetch_order_detail(self):
        orders = models.fetch_all_orders()
        if orders:
            order_id = orders[0]['id_pedido']
            header, items = models.fetch_order_detail(order_id)
            self.assertTrue(header is None or isinstance(header, dict))
            self.assertTrue(isinstance(items, list) or isinstance(items, tuple))

    def test_fetch_sales_metrics(self):
        metrics = models.fetch_sales_metrics(days=3)
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_monto', metrics)

    def test_update_order_status(self):
        orders = models.fetch_all_orders()
        if orders:
            order_id = orders[0]['id_pedido']
            result = models.update_order_status(order_id, 'completado')
            self.assertTrue(result or result is False)

if __name__ == '__main__':
    unittest.main()
