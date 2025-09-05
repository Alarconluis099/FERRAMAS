from flask import Blueprint, flash, request, redirect, url_for, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from app import app
from app import mysql  # real mysql (fallback)

# Wrapper diferido: permite monkeypatch en tests usando app.routes.mysql
def _mysql():
    try:
        from app import routes as _r  # type: ignore
        if hasattr(_r, 'mysql'):
            return getattr(_r, 'mysql')
    except Exception:
        pass
    return mysql

auth_bp = Blueprint('auth', __name__)

# Helpers reutilizados (role fetch)

def _fetch_role(username):
    try:
        cur = _mysql().connection.cursor()
        cur.execute("SELECT role FROM users WHERE usuario=%s", (username,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    except Exception:
        return None

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = session.get('usuario')
            if not user:
                flash('Acceso restringido.', 'error')
                return redirect(url_for('bp.inicio'))
            role = _fetch_role(user) or ('admin' if user == 'admin' else None)
            if role not in roles:
                flash('Permisos insuficientes.', 'error')
                return redirect(url_for('bp.inicio'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

@auth_bp.route('/guardar_registro', methods=['POST'])
def guardar_registro():
    form = request.form
    username = (form.get('usuario_nombre') or '').strip()
    correo = (form.get('usuario_correo') or '').strip().lower()
    pass1 = form.get('usuario_contraseña','')
    if not all([username, correo, pass1]):
        flash('Completa todos los campos.', 'error'); return redirect(url_for('bp.registro'))
    import re
    if not re.match(r'^[A-Za-z0-9._%+-]+@gmail\.com$', correo):
        flash('Debe ser un correo @gmail.com válido.', 'error'); return redirect(url_for('bp.registro'))
    if len(pass1) < 8:
        flash('La contraseña debe tener al menos 8 caracteres.', 'error'); return redirect(url_for('bp.registro'))
    cursor = _mysql().connection.cursor()
    cursor.execute("SELECT 1 FROM users WHERE correo=%s OR usuario=%s", (correo, username))
    if cursor.fetchone():
        flash('Correo o usuario ya registrados.', 'error'); cursor.close(); return redirect(url_for('bp.registro'))
    hashed = generate_password_hash(pass1)
    role = 'user'
    if username.lower() == 'admin':
        cur2 = _mysql().connection.cursor()
        cur2.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
        if (cur2.fetchone() or [0])[0] == 0:
            role = 'admin'
        cur2.close()
    try:
        cursor.execute("INSERT INTO users (correo, contraseña, usuario, descuento_porcentaje, role) VALUES (%s,%s,%s,%s,%s)", (correo, hashed, username, 15, role))
    except Exception:
        cursor.close(); flash('Error creando usuario.', 'error'); return redirect(url_for('bp.registro'))
    _mysql().connection.commit(); cursor.close(); flash('Cuenta creada. Ahora puedes iniciar sesión.', 'success')
    return redirect(url_for('bp.iniciar_sesion'))

@auth_bp.route('/iniciar_sesion', methods=['POST', 'GET'])
def iniciar_sesion():
    if request.method != 'POST':
        return render_template('login.html')
    user_input = (request.form.get('usuario_correo') or '').strip()
    password = request.form.get('usuario_contraseña') or ''
    if not user_input or not password:
        flash('Ingresa tu correo/usuario y la contraseña.', 'error'); return redirect(url_for('bp.iniciar_sesion'))
    import re
    es_correo = re.match(r'^[A-Za-z0-9._%+-]+@gmail\.com$', user_input.lower()) is not None
    cursor = _mysql().connection.cursor()
    try:
        if es_correo:
            cursor.execute("SELECT id_user, usuario, contraseña, COALESCE(descuento_porcentaje,0), COALESCE(role,'') FROM users WHERE correo=%s", (user_input.lower(),))
        else:
            cursor.execute("SELECT id_user, usuario, contraseña, COALESCE(descuento_porcentaje,0), COALESCE(role,'') FROM users WHERE usuario=%s", (user_input,))
        result = cursor.fetchone()
        if not result:
            cursor.close(); flash('Credenciales inválidas.', 'error'); return redirect(url_for('bp.iniciar_sesion'))
        usuario_id, usuario_nombre, stored_pass, descuento_pct, role = result
        is_hashed = stored_pass.startswith(('pbkdf2:', 'scrypt:'))
        try:
            if is_hashed:
                valid = check_password_hash(stored_pass, password)
            else:
                if app.config.get('LEGACY_PLAIN_PASSWORD_ALLOWED'):
                    valid = (stored_pass == password)
                    if valid:
                        try:
                            new_hash = generate_password_hash(password)
                            up = _mysql().connection.cursor(); up.execute("UPDATE users SET contraseña=%s WHERE id_user=%s", (new_hash, usuario_id)); _mysql().connection.commit(); up.close()
                        except Exception:
                            _mysql().connection.rollback()
                else:
                    valid = False
        except Exception:
            valid = False
        cursor.close()
        if not valid:
            flash('Credenciales inválidas.', 'error'); return redirect(url_for('bp.iniciar_sesion'))
        from datetime import timedelta
        session['usuario'] = usuario_nombre
        remember = request.form.get('remember_me') == '1'
        if remember:
            session.permanent = True; app.permanent_session_lifetime = timedelta(days=30)
        else:
            session.permanent = False
        return redirect(url_for('bp.inicio'))
    except Exception:
        try:
            cursor.close()
        except Exception:
            pass
        flash('Error en autenticación.', 'error'); return redirect(url_for('bp.iniciar_sesion'))

@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None); return redirect(url_for('bp.inicio'))

@auth_bp.route('/Login')
def login_alias():
    return render_template('login.html', cart_count=0)

@auth_bp.route('/Registro')
def registro():
    return render_template('registro.html', cart_count=0)

# Exponer decoradores
admin_required = lambda f: role_required('admin')(f)
staff_or_admin_required = lambda f: role_required('admin','staff')(f)
