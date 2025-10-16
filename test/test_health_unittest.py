import unittest
from app import app

class TestHealthRoute(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_health(self):
        resp = self.app.get('/health')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('status', resp.json)
        self.assertIn(resp.json['status'], ['ok', 'healthy'])

if __name__ == '__main__':
    unittest.main()
