import unittest
from unittest.mock import patch, MagicMock
from flask_testing import TestCase
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

class CartFlowTest(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        return app

    def setUp(self):
        # Patch MySQL connection + cursor
        self.patcher_conn = patch('flask_mysqldb.MySQL.connection')
        mocked_conn = self.patcher_conn.start()
        self.mock_cursor = MagicMock()
        mocked_conn.cursor.return_value = self.mock_cursor
        # Basic user lookup for _current_user_id()
        # Sequence of fetchone / fetchall responses used by different calls.
        # We'll tailor side_effect to simulate simple scenarios.
        # fetchone for SELECT id_user FROM users WHERE usuario=%s
        self.mock_cursor.fetchone.return_value = (1,)  # user id 1
        # fetchall for listing tools (unused in these tests, but keep shape)
        self.mock_cursor.fetchall.return_value = []
        self.mock_cursor.description = []
        # Simulate session login
        with self.client.session_transaction() as sess:
            sess['usuario'] = 'tester'

    def tearDown(self):
        self.patcher_conn.stop()

    @patch('app.routes.cart.get_user_open_order')
    @patch('app.routes.cart.get_cart_items')
    @patch('app.routes.cart.get_cart_totals')
    @patch('app.routes.cart.add_or_update_item')
    @patch('app.routes.cart.get_or_create_order')
    @patch('app.routes.cart.get_user_discount')
    def test_api_add_and_list_items(self, mock_discount, mock_get_or_create, mock_add_update, mock_totals, mock_get_items, mock_get_open):
        mock_discount.return_value = 0
        mock_get_or_create.return_value = 10  # order id
        mock_add_update.return_value = True
        mock_totals.return_value = (0, 1)  # subtotal, count
        mock_get_open.return_value = 10
        mock_get_items.return_value = [{
            'id_tool': 123,
            'cantidad': 1,
            'precio_unitario': 1000,
            'subtotal_linea': 1000,
            'name': 'Martillo'
        }]

        # Add item via API
        r = self.client.post('/api/guardar_pedido', json={'product_id': 123, 'cantidad': 1})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json.get('ok'))
        self.assertEqual(r.json.get('cart_count'), 1)

        # List items via /Pedido
        r2 = self.client.get('/Pedido')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(r2.json), 1)
        self.assertEqual(r2.json[0]['id_tool'], 123)

    @patch('app.routes.cart.get_user_open_order')
    def test_empty_cart_returns_redirect(self, mock_get_open):
        mock_get_open.return_value = None
        resp = self.client.get('/Carrito', follow_redirects=False)
        # Without open order user should be redirected to inicio
        self.assertIn(resp.status_code, (301,302))

if __name__ == '__main__':
    unittest.main()
