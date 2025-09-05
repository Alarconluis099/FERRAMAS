import unittest
from unittest.mock import patch, MagicMock
from flask_testing import TestCase
from werkzeug.security import generate_password_hash
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app  # noqa: E402


class AuthTest(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        return app

    def setUp(self):
        patcher = patch('flask_mysqldb.MySQL.connection')
        self.addCleanup(patcher.stop)
        mocked_connection = patcher.start()
        self.mock_cursor = MagicMock()
        mocked_connection.cursor.return_value = self.mock_cursor
        self.hashed = generate_password_hash('Secret123!')

    def test_login_success(self):
        # Simula consulta de usuario por username
        self.mock_cursor.fetchone.return_value = (1, 'user1', self.hashed, 0, 'user')
        resp = self.client.post('/iniciar_sesion', data={
            'usuario_correo': 'user1',
            'usuario_contraseña': 'Secret123!'
        }, follow_redirects=False)
        self.assertIn(resp.status_code, (302, 303))  # redirect al inicio
        # Verifica que fetchone fue usada
        self.mock_cursor.fetchone.assert_called()

    def test_login_failure_wrong_password(self):
        self.mock_cursor.fetchone.return_value = (1, 'user1', self.hashed, 0, 'user')
        resp = self.client.post('/iniciar_sesion', data={
            'usuario_correo': 'user1',
            'usuario_contraseña': 'BADPASS'
        })
        self.assertEqual(resp.status_code, 302)  # redirect back to login

    def test_login_user_not_found(self):
        self.mock_cursor.fetchone.return_value = None
        resp = self.client.post('/iniciar_sesion', data={
            'usuario_correo': 'ghost',
            'usuario_contraseña': 'whatever'
        })
        self.assertEqual(resp.status_code, 302)


if __name__ == '__main__':
    unittest.main()
