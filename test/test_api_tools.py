import unittest
from unittest.mock import patch
from flask_testing import TestCase
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app  # noqa: E402


class ApiToolsTest(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        return app

    @patch('app.routes.fetch_tools_filtered', return_value=([{'id_tool': 1, 'name': 'X', 'stock': 5, 'precio': 1000}], 1))
    def test_api_tools_basic(self, _):
        r = self.client.get('/api/tools?page=1&per_page=20')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json['ok'])
        self.assertEqual(r.json['total'], 1)
        self.assertEqual(len(r.json['items']), 1)


if __name__ == '__main__':
    unittest.main()
