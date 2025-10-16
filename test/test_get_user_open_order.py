import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from app import models

class TestGetUserOpenOrder(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        self.users = models.get_all_users()
        self.user_id = self.users[0]['id_user'] if self.users else None
    def tearDown(self):
        self.app_context.pop()
    def test_get_user_open_order(self):
        order_id = models.get_user_open_order(self.user_id)
        self.assertTrue(order_id is None or isinstance(order_id, int))

if __name__ == '__main__':
    unittest.main()
