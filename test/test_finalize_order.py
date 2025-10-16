import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from app import models

class TestFinalizeOrder(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        self.users = models.get_all_users()
        self.user_id = self.users[0]['id_user'] if self.users else None
        self.tools = models.fetch_all_tools()
        self.tool_id = self.tools[0]['id_tool'] if self.tools else None
    def tearDown(self):
        self.app_context.pop()
    def test_finalize_order(self):
        order_id = models.get_or_create_order(self.user_id)
        models.add_or_update_item(order_id, self.tool_id, 1)
        total, _ = models.get_cart_totals(order_id)
        models.finalize_order(order_id, total)
        # solo que no falle

if __name__ == '__main__':
    unittest.main()
