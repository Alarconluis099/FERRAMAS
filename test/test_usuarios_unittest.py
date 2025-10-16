import unittest
from app import app
from app import models
from flask import current_app

class TestUsuarios(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_get_all_users(self):
        users = models.get_all_users()
        self.assertIsInstance(users, list)

    def test_fetch_users_by_id(self):
        users = models.get_all_users()
        if users:
            user_id = users[0].get('id_user')
            user = models.fetch_users_by_id(user_id)
            self.assertIsInstance(user, dict)

    def test_get_usuario_by_usuario(self):
        users = models.get_all_users()
        if users:
            usuario = users[0].get('usuario')
            info = models.get_usuario_by_usuario(usuario)
            self.assertTrue(info is None or isinstance(info, dict))

    def test_get_user_discount(self):
        users = models.get_all_users()
        if users:
            usuario = users[0].get('usuario')
            discount = models.get_user_discount(usuario)
            self.assertIsInstance(discount, int)

if __name__ == '__main__':
    unittest.main()
