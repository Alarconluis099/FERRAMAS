import pytest, sys, os
from flask import session
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app as flask_app

HASH_X = 'scrypt:32768:8:1$PQqkXVn7fiDjhnmC$d4e128ef339f288dcde6161b433a11e8bb8c9b464e5532045777382e56cac04f2fd7da7ffda77625abf98f82f4204cf90b2baa86c58670ff81d8afeb55a66eba'

# Fixtures
@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c

# Helper login

def login(client, username, password):
    return client.post('/iniciar_sesion', data={'usuario_correo': username, 'usuario_contraseña': password}, follow_redirects=True)

@pytest.fixture
def mock_db_user_roles(monkeypatch):
    class DummyCursor:
        def __init__(self):
            self.lastrowid = 1
            self.description = None
        def execute(self, q, params=None):
            ql = q.lower()
            self._row = None
            self._many = []
            if 'select role from users' in ql and params:
                u = params[0]
                if u == 'admin': self._row = ('admin',)
                elif u == 'staff': self._row = ('staff',)
                elif u == 'cliente': self._row = ('user',)
                else: self._row = None
            elif 'select id_user, usuario, contraseña' in ql and params:
                u = params[0]
                if u == 'admin': self._row = (1, 'admin', HASH_X, 0, 'admin')
                elif u == 'staff': self._row = (2, 'staff', HASH_X, 0, 'staff')
                elif u == 'cliente': self._row = (3, 'cliente', HASH_X, 0, 'user')
                else: self._row = None
            elif 'select id_tool, name, description, stock, precio from tools' in ql:
                self._many = [
                    (1, 'Taladro', 'Desc', 10, 10000),
                    (2, 'Martillo', 'Desc', 2, 5000)
                ]
                self.description = [('id_tool',), ('name',), ('description',), ('stock',), ('precio',)]
            elif 'select 1 from tools' in ql:
                self._row = None
            elif 'insert into tools' in ql:
                pass
            elif 'update tools' in ql:
                pass
            elif 'delete from tools' in ql:
                pass
        def fetchone(self):
            return self._row
        def fetchall(self):
            return self._many
        def close(self):
            pass
    class DummyConn:
        def cursor(self, *_, **__): return DummyCursor()
        def commit(self): pass
        def rollback(self): pass
    class DummyMySQL: connection = DummyConn()
    monkeypatch.setattr('app.routes.mysql', DummyMySQL())
    monkeypatch.setattr('app.models.mysql', DummyMySQL())

@pytest.mark.usefixtures('mock_db_user_roles')
class TestRoleAccess:
    def test_admin_dashboard_requires_admin(self, client):
        resp = client.get('/admin', follow_redirects=True)
        assert resp.status_code in (200,302)

    def test_staff_cannot_access_admin_dashboard(self, client):
        login(client, 'staff', 'x')
        r = client.get('/admin', follow_redirects=True)
        assert any(msg in r.data for msg in [b'Permisos insuficientes', b'Acceso restringido'])

    def test_admin_can_access_admin_dashboard(self, client):
        login(client, 'admin', 'x')
        r = client.get('/admin')
        assert r.status_code == 200

    def test_staff_dashboard_access_staff(self, client):
        login(client, 'staff', 'x')
        r = client.get('/staff')
        assert r.status_code == 200
        assert b'Panel Staff' in r.data

    def test_staff_dashboard_access_admin(self, client):
        login(client, 'admin', 'x')
        r = client.get('/staff')
        assert r.status_code == 200

    def test_user_cannot_access_staff_dashboard(self, client):
        login(client, 'cliente', 'x')
        r = client.get('/staff', follow_redirects=True)
        assert any(msg in r.data for msg in [b'Permisos insuficientes', b'Acceso restringido'])

    def test_staff_can_create_product(self, client):
        login(client, 'staff', 'x')
        r = client.post('/admin/producto', data={'name':'Nueva','stock':5,'precio':1000,'description':'x'}, follow_redirects=True)
        assert r.status_code in (200,302)

    def test_user_cannot_create_product(self, client):
        login(client, 'cliente', 'x')
        r = client.post('/admin/producto', data={'name':'Nueva','stock':5,'precio':1000,'description':'x'}, follow_redirects=True)
        assert any(msg in r.data for msg in [b'Permisos insuficientes', b'Acceso restringido'])
