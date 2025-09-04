import unittest
from unittest.mock import patch, MagicMock
from flask_testing import TestCase
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app


class RoutesTest(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        return app

    def setUp(self):
        self.patcher = patch('flask_mysqldb.MySQL.connection')
        mocked_connection = self.patcher.start()
        self.mock_cursor = MagicMock()
        mocked_connection.cursor.return_value = self.mock_cursor
        # fetch_all_tools query returns (id_tool, name, description, stock, precio)
        self.mock_cursor.fetchall.return_value = [
            (100, 'Martillo', 'Herramienta de mano', 100, 19990),
            (110, 'Caja de Clavos', 'Pieza metálica', 100, 5990)
        ]
        self.mock_cursor.description = [
            ('id_tool',), ('name',), ('description',), ('stock',), ('precio',)
        ]

    def tearDown(self):
        self.patcher.stop()

    def test_get_tools(self):
        resp = self.client.get('/tools')
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json, list)
        self.assertGreater(len(resp.json), 0)
        self.assertIn('id_tool', resp.json[0])
        self.assertNotIn('id_tools_type', resp.json[0])

    @patch('app.routes.delete_tools')
    def test_delete_tool(self, mock_delete):
        mock_delete.return_value = True
        r = self.client.delete('/tools/100')
        self.assertEqual(r.status_code, 200)
        mock_delete.return_value = False
        r = self.client.delete('/tools/999')
        self.assertEqual(r.status_code, 404)

    @patch('app.routes.update_tools')
    def test_update_tool(self, mock_update):
        mock_update.return_value = True
        payload = {"id_tool": 100, "name": "Martillo Pro", "description": "Acero", "stock": 90, "precio": 20990}
        r = self.client.put('/tools/100', json=payload)
        self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main()