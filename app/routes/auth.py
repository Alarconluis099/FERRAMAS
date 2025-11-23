from flask import Blueprint, request, session, jsonify, current_app, flash, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from app import app
from app import mysql
from app.models import finalize_order, get_cart_items

auth_bp = Blueprint('auth', __name__)
__all__ = ['auth_bp']

# Endpoint de mantenimiento: fuerza transacciones pendientes a AUTHORIZED y actualiza pedido
@auth_bp.route('/__admin/fix_transacciones_pendientes', methods=['POST'])
def fix_transacciones_pendientes():
    if not session.get('rol') == 'admin':
        return jsonify({'ok': False, 'error': 'Solo admin'}), 403
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_transaccion, id_pedido, monto_transaccion, status FROM transacciones WHERE status='pending'")
    rows = cur.fetchall()
    result = []
    for id_tx, id_pedido, monto, status in rows:
        # Busca el monto real actual del pedido
        monto_real = None
        if id_pedido:
            cur.execute("SELECT monto_total, estado_pedido FROM pedidos WHERE id_pedido=%s", (id_pedido,))
            pedido_row = cur.fetchone()
            if pedido_row:
                monto_real, estado_pedido = pedido_row
            else:
                estado_pedido = None
        else:
            estado_pedido = None
        result.append({
            'id_transaccion': id_tx,
            'id_pedido': id_pedido,
            'monto_transaccion': monto,
            'status': status,
            'pedido_monto_total': monto_real,
            'pedido_estado': estado_pedido
        })
    cur.close()
    return jsonify({'ok': True, 'pendientes': result})

from flask import Blueprint, request, session, jsonify, current_app
from app import mysql
from app.models import finalize_order, get_cart_items

auth_bp = Blueprint('auth', __name__)
__all__ = ['auth_bp']

# Endpoint de mantenimiento: repara pedidos pendientes con productos y monto 0
@auth_bp.route('/__admin/fix_pedidos_pendientes', methods=['POST'])
def fix_pedidos_pendientes():
    if not session.get('rol') == 'admin':
        return jsonify({'ok': False, 'error': 'Solo admin'}), 403
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_pedido, estado_pedido, monto_total FROM pedidos WHERE estado_pedido IN ('pendiente','enviado') AND monto_total=0")
    rows = cur.fetchall()
    result = []
    for order_id, estado, monto in rows:
        items = get_cart_items(order_id)
        total = 0
        for it in items:
            subtotal = (it.get('cantidad') or 0) * (it.get('precio_unitario') or 0)
            total += subtotal
        # Si el monto_total es 0 y el calculado es mayor a 0, actualiza solo el monto_total
        if (monto is None or monto == 0) and total > 0:
            try:
                cur.execute("UPDATE pedidos SET monto_total=%s WHERE id_pedido=%s", (total, order_id))
                mysql.connection.commit()
                monto = total
            except Exception as e:
                mysql.connection.rollback()
                current_app.logger.error('[FIX_MONTOS_SOLO] Error actualizando monto_total en pedido %s: %s', order_id, e)
        result.append({
            'id_pedido': order_id,
            'estado_pedido': estado,
            'monto_total': monto,
            'monto_calculado': total,
            'items': items
        })
    cur.close()
    return jsonify({'ok': True, 'pendientes': result})
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
        # Guardar id_user en session para evitar consultas repetidas
        try:
            session['id_user'] = int(usuario_id)
        except Exception:
            try:
                session.pop('id_user', None)
            except Exception:
                pass
        # Guardar rol en sesión para que la barra de navegación pueda mostrar enlaces admin/staff
        try:
            session['rol'] = role or ('admin' if usuario_nombre == 'admin' else None)
        except Exception:
            session['rol'] = ('admin' if usuario_nombre == 'admin' else None)
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
    session.pop('usuario', None)
    session.pop('rol', None)
    return redirect(url_for('bp.inicio'))

@auth_bp.route('/Login')
def login_alias():
    return render_template('login.html', cart_count=0)

@auth_bp.route('/Registro')
def registro():
    return render_template('registro.html', cart_count=0)

# Exponer decoradores
admin_required = lambda f: role_required('admin')(f)
staff_or_admin_required = lambda f: role_required('admin','staff')(f)


# Endpoint de test para setear sesión como un usuario específico.
# SOLO activo cuando DEBUG o TESTING están habilitados.
@auth_bp.route('/__test/login_as', methods=['POST'])
def __test_login_as():
    from flask import current_app, jsonify
    if not (current_app.debug or current_app.config.get('TESTING')):
        return jsonify({'ok': False, 'error': 'Not allowed'}), 403
    data = request.get_json(silent=True) or request.form or {}
    usuario = (data.get('usuario') or data.get('user') or request.headers.get('X-Test-User') or '').strip()
    if not usuario:
        return jsonify({'ok': False, 'error': 'usuario missing'}), 400
    try:
        cur = _mysql().connection.cursor()
        cur.execute("SELECT id_user, usuario FROM users WHERE usuario=%s OR correo=%s", (usuario, usuario))
        row = cur.fetchone()
        cur.close()
        if not row:
            return jsonify({'ok': False, 'error': 'user not found'}), 404
        uid = row[0]
        uname = row[1] if len(row) > 1 else usuario
        # Setear en session
        session['usuario'] = uname
        try:
            session['id_user'] = int(uid)
        except Exception:
            session.pop('id_user', None)
        # role if exists
        try:
            cur2 = _mysql().connection.cursor()
            cur2.execute("SELECT COALESCE(role,'') FROM users WHERE id_user=%s", (uid,))
            rrow = cur2.fetchone(); cur2.close()
            session['rol'] = (rrow[0] or ('admin' if uname == 'admin' else None))
        except Exception:
            session['rol'] = ('admin' if uname == 'admin' else None)
        return jsonify({'ok': True, 'usuario': uname, 'id_user': uid})
    except Exception as e:
        try:
            cur.close()
        except Exception:
            pass
        return jsonify({'ok': False, 'error': 'db error', 'detail': str(e)}), 500


# Endpoint debug para inspeccionar cookies y sesión (solo DEBUG/TESTING)
@auth_bp.route('/__debug/cookies')
def __debug_cookies():
    from flask import current_app, jsonify
    if not (current_app.debug or current_app.config.get('TESTING')):
        return jsonify({'ok': False, 'error': 'Not allowed'}), 403
    try:
        # Convertir session a dict de forma segura
        s = {}
        for k in list(session.keys()):
            try:
                s[k] = session.get(k)
            except Exception:
                s[k] = '<unserializable>'
        return jsonify({'ok': True, 'cookies': dict(request.cookies), 'session': s})
    except Exception as e:
        return jsonify({'ok': False, 'error': 'internal', 'detail': str(e)}), 500
