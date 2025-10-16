import unittest
from app import app
from app import models
from flask import current_app

class TestRolesMetrica(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        self.users = models.get_all_users()

    def tearDown(self):
        self.app_context.pop()

    def test_user_roles(self):
        if self.users:
            user = self.users[0]
            self.assertIn('role', user)

    def test_user_discount(self):
        if self.users:
            usuario = self.users[0].get('usuario')
            discount = models.get_user_discount(usuario)
            self.assertIsInstance(discount, int)

    def test_fetch_sales_metrics(self):
        metrics = models.fetch_sales_metrics(days=7)
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_orders', metrics)

    def test_fetch_top_products(self):
        top = models.fetch_top_products(limit=3)
        self.assertTrue(isinstance(top, list) or isinstance(top, tuple))

if __name__ == '__main__':
    unittest.main()
