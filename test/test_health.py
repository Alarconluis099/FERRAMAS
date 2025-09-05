import unittest
from unittest.mock import patch, MagicMock
from flask_testing import TestCase
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app  # noqa: E402


class HealthTest(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        return app

    @patch('flask_mysqldb.MySQL.connection')
    def test_health(self, mock_conn):
        mock_cur = MagicMock(); mock_conn.cursor.return_value = mock_cur
        r = self.client.get('/health')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json['ok'])

    @patch('flask_mysqldb.MySQL.connection')
    def test_ready_ok(self, mock_conn):
        mock_cur = MagicMock(); mock_conn.cursor.return_value = mock_cur
        r = self.client.get('/ready')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json['ok'])


if __name__ == '__main__':
    unittest.main()
