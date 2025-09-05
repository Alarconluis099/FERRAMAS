import unittest
from unittest.mock import patch
from flask_testing import TestCase
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app  # noqa: E402


class CartTest(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        return app

    @patch('app.routes.get_cart_totals', return_value=(10000, 3))
    @patch('app.routes.add_or_update_item', return_value=True)
    @patch('app.routes.get_or_create_order', return_value=55)
    @patch('app.routes._current_user_id', return_value=9)
    def test_api_add_item(self, *_):
        resp = self.client.post('/api/guardar_pedido', json={'product_id': 120, 'cantidad': 2})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json['ok'])
        self.assertEqual(resp.json['cart_count'], 3)

    @patch('app.routes._current_user_id', return_value=None)
    def test_api_add_item_unauthorized(self, _):
        resp = self.client.post('/api/guardar_pedido', json={'product_id': 120, 'cantidad': 1})
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()
