import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from app import models

class TestGetCartItems(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        self.users = models.get_all_users()
        self.user_id = self.users[0]['id_user'] if self.users else None
    def tearDown(self):
        self.app_context.pop()
    def test_get_cart_items(self):
        order_id = models.get_or_create_order(self.user_id)
        items = models.get_cart_items(order_id)
        self.assertTrue(isinstance(items, list) or isinstance(items, tuple))

if __name__ == '__main__':
    unittest.main()
