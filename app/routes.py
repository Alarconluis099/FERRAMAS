from flask import flash, request, Blueprint, jsonify, render_template, redirect, url_for, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from .models import (
    fetch_all_tools,
    fetch_tools_by_code,
    insert_tools,
    delete_tools,
    update_tools,
    get_all_users,
    fetch_users_by_id,
    get_usuario_by_usuario,
    # nuevo esquema
    get_or_create_order,
    add_or_update_item,
    remove_item,
    get_cart_items,
    get_cart_totals,
    set_item_quantity,
    get_user_open_order,
    clear_order_items,
)
from . import mysql
import random


bp = Blueprint('bp', __name__)

def _current_user_id():
    if 'usuario' not in session:
        return None
    # look up id_user by username
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id_user FROM users WHERE usuario=%s", (session['usuario'],))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None
    except Exception:
        return None

def _get_cart_count():
    user_id = _current_user_id()
    if not user_id:
        return 0
    order_id = get_user_open_order(user_id)
    if not order_id:
        return 0
    _, count = get_cart_totals(order_id)
    return count

# Ruta legacy /pedido eliminada (normalización de esquema). Si se requiere, implementar listado de pedido actual.


@bp.route('/disminuir_cantidad/<int:id_tool>', methods=['POST'])
def disminuir_cantidad(id_tool):
    user_id = _current_user_id()
    if not user_id:
        return redirect(url_for('bp.inicio'))
    order_id = get_user_open_order(user_id)
    if not order_id:
        return redirect(url_for('bp.inicio'))
    # obtener cantidad actual
    items = get_cart_items(order_id)
    for it in items:
        if it['id_tool'] == id_tool:
            new_q = it['cantidad'] - 1
            set_item_quantity(order_id, id_tool, new_q)
            break
    return redirect(url_for('bp.carrito'))



@bp.route('/aumentar_cantidad/<int:id_tool>', methods=['POST'])
def aumentar_cantidad(id_tool):
    user_id = _current_user_id()
    if not user_id:
        return redirect(url_for('bp.inicio'))
    order_id = get_or_create_order(user_id)
    add_or_update_item(order_id, id_tool, 1)
    return redirect(url_for('bp.carrito'))

@bp.route('/eliminar_item/<int:id_tool>', methods=['POST'])
def eliminar_item(id_tool):
    user_id = _current_user_id()
    if user_id:
        order_id = get_user_open_order(user_id)
        if order_id:
            remove_item(order_id, id_tool)
    flash('Producto eliminado del carrito', 'info')
    return redirect(url_for('bp.carrito'))


@bp.route('/guardar_registro', methods=['POST'])
def guardar_registro():
    """Registro simplificado: usuario_nombre (username), usuario_correo (gmail), usuario_contraseña (sin repetición)."""
    form = request.form
    username = (form.get('usuario_nombre') or '').strip()
    correo = (form.get('usuario_correo') or '').strip().lower()
    pass1 = form.get('usuario_contraseña','')

    if not all([username, correo, pass1]):
        flash('Completa todos los campos.', 'error')
        return redirect(url_for('bp.registro'))

    import re
    if not re.match(r'^[A-Za-z0-9._%+-]+@gmail\.com$', correo):
        flash('Debe ser un correo @gmail.com válido.', 'error')
        return redirect(url_for('bp.registro'))
    if len(pass1) < 8:
        flash('La contraseña debe tener al menos 8 caracteres.', 'error')
        return redirect(url_for('bp.registro'))

    cursor = mysql.connection.cursor()
    # Unicidad de correo y usuario
    cursor.execute("SELECT 1 FROM users WHERE correo=%s OR usuario=%s", (correo, username))
    if cursor.fetchone():
        flash('Correo o usuario ya registrados.', 'error')
        cursor.close()
        return redirect(url_for('bp.registro'))

    hashed = generate_password_hash(pass1)
    cursor.execute(
        "INSERT INTO users (correo, contraseña, usuario, descuento_porcentaje) VALUES (%s,%s,%s,%s)",
        (correo, hashed, username, 15)
    )
    mysql.connection.commit()
    cursor.close()
    flash('Cuenta creada. Ahora puedes iniciar sesión.', 'success')
    return redirect(url_for('bp.iniciar_sesion'))




@bp.route('/iniciar_sesion', methods=['POST', 'GET'])
def iniciar_sesion():
    if request.method == 'POST':
        usuario_correo = request.form.get('usuario_correo')
        usuario_contraseña = request.form.get('usuario_contraseña')

        if not usuario_correo or not usuario_contraseña:
            flash('Por favor, ingrese tanto el correo como la contraseña.', 'error')
            return redirect(url_for('bp.iniciar_sesion'))

        # Validación formato gmail
        correo_normalizado = usuario_correo.strip().lower()
        import re
        if not re.match(r'^[A-Za-z0-9._%+-]+@gmail\.com$', correo_normalizado):
            flash('El correo debe ser un correo @gmail.com válido.', 'error')
            return redirect(url_for('bp.iniciar_sesion'))

        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id_user, usuario, contraseña, COALESCE(descuento_porcentaje,0) FROM users WHERE correo = %s",
            (correo_normalizado,)
        )
        result = cursor.fetchone()
        if not result:
            cursor.close()
            flash('Correo y/o contraseña inválidos.', 'error')
            return redirect(url_for('bp.iniciar_sesion'))

        usuario_id, usuario_nombre, stored_pass, descuento_pct = result

        # Detección de hash (formatos Werkzeug comienzan con 'pbkdf2:' o similares)
        is_hashed = stored_pass.startswith('pbkdf2:') or stored_pass.startswith('scrypt:')
        valid = False
        try:
            if is_hashed:
                valid = check_password_hash(stored_pass, usuario_contraseña)
            else:
                # Legacy plaintext: comparar directo y luego migrar a hash
                valid = (stored_pass == usuario_contraseña)
                if valid:
                    try:
                        new_hash = generate_password_hash(usuario_contraseña)
                        up = mysql.connection.cursor()
                        up.execute("UPDATE users SET contraseña=%s WHERE id_user=%s", (new_hash, usuario_id))
                        mysql.connection.commit()
                        up.close()
                    except Exception:
                        mysql.connection.rollback()
        except Exception:
            valid = False

        cursor.close()
        if not valid:
            flash('Correo y/o contraseña inválidos.', 'error')
            return redirect(url_for('bp.iniciar_sesion'))

        session['usuario'] = usuario_nombre
        session.permanent = True
        # descuento_pct se mantiene para lógica futura; ya disponible en variable
        return redirect(url_for('bp.inicio'))

    return render_template('login.html')


    

@bp.route('/guardar_pedido', methods=['POST'])
def guardar_pedido():
    user_id = _current_user_id()
    if not user_id:
        flash('Inicia sesión para agregar productos.', 'error')
        return redirect(url_for('bp.login'))
    try:
        product_id = int(request.form['product_id'])
        cantidad = int(request.form.get('cantidad', 1))
    except Exception:
        flash('Datos de producto inválidos', 'error')
        return redirect(url_for('bp.inicio'))
    order_id = get_or_create_order(user_id)
    add_or_update_item(order_id, product_id, cantidad)
    return redirect(url_for('bp.inicio'))

@bp.route('/api/guardar_pedido', methods=['POST'])
def api_guardar_pedido():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'ok':False,'error':'Debes iniciar sesión'}), 401
    data = request.get_json(silent=True) or {}
    try:
        product_id = int(data.get('product_id'))
        cantidad = int(data.get('cantidad', 1))
    except Exception:
        return jsonify({'ok':False,'error':'Datos inválidos'}), 400
    order_id = get_or_create_order(user_id)
    if not add_or_update_item(order_id, product_id, cantidad):
        return jsonify({'ok':False,'error':'No se pudo agregar'}), 500
    # Recalcular total items
    _, count = get_cart_totals(order_id)
    return jsonify({'ok':True,'cart_count': count})



@bp.route('/Pedido', methods=['GET'])
def pedido():
    # Retorna items de la orden abierta del usuario
    user_id = _current_user_id()
    if not user_id:
        return jsonify([])
    order_id = get_user_open_order(user_id)
    if not order_id:
        return jsonify([])
    return jsonify(get_cart_items(order_id))

@bp.route('/users', methods=['GET'])
def get_users():
    users = get_all_users()
    return jsonify(users)

# Ruta duplicada eliminada / comentada
# @bp.route('/users', methods=['GET'])
# def get_users_by_id():
#     pass

@bp.route('/tools', methods=['GET'])
def get_tools():
    return jsonify(fetch_all_tools())


@bp.route('/tools/<code>', methods=['GET'])
def get_tool(code):
    return jsonify(fetch_tools_by_code(code))


@bp.route('/tool', methods=['POST'])
def create_tools():
    tools_data = request.get_json(silent=True) or {}
    required = {'id_tool','name'}
    if not required.issubset(tools_data):
        return jsonify({'error':'Faltan campos requeridos'}), 400
    if insert_tools(tools_data):
        return jsonify({'message': 'Herramienta creada exitosamente'}), 201
    return jsonify({'error':'Error al crear herramienta'}), 500


@bp.route('/pedido/<id_pedido>', methods=['GET'])
def get_pedido(id_pedido):
    # Totales de un pedido específico (si existiera) - simplificado
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT monto_total, estado_pedido FROM pedidos WHERE id_pedido=%s", (id_pedido,))
        row = cursor.fetchone()
        if not row:
            return jsonify({}), 404
        return jsonify({'monto_total': row[0], 'estado_pedido': row[1]})
    finally:
        cursor.close()


@bp.route('/tools/<id>', methods=['DELETE'])
def delete_tool_route(id):
    try:
        if delete_tools(id):
            return jsonify({'message': 'Herramienta eliminada correctamente'}), 200
        return jsonify({'message': 'Herramienta no encontrada'}), 404
    except Exception as e:
        current_app.logger.exception("Error deleting tool")
        return jsonify({'Error': 'Error del servidor'}), 500
    

@bp.route('/tools/<id>', methods=['PUT'])
def update_tool_route(id):
    try:
        tools_data = request.get_json(silent=True) or {}
        if update_tools(id, tools_data):
            return jsonify({'message': 'Herramienta actualizada correctamente'}), 200
        return jsonify({'message': 'Herramienta no encontrada'}), 404
    except Exception as e:
        current_app.logger.exception("Error updating tool")
        return jsonify({'Error': 'Error del servidor'}), 500
    
@bp.route('/')
def main():
    return redirect(url_for('bp.inicio'))

@bp.route('/Cliente')
def cliente():
    usuario = session.get('usuario')
    if not usuario:
        return redirect(url_for('bp.iniciar_sesion'))
    return render_template('Cliente.html', usuario=usuario, cart_count=_get_cart_count())


from decimal import Decimal
import pdb


@bp.route('/Carrito')
@bp.route('/carrito')  # alias en minúsculas
def carrito():
    usuario = session.get('usuario')
    user_id = _current_user_id()
    if not user_id:
        return redirect(url_for('bp.inicio'))
    order_id = get_user_open_order(user_id)
    pedidos = get_cart_items(order_id) if order_id else []
    from decimal import Decimal
    subtotal = Decimal(0)
    for p in pedidos:
        subtotal += Decimal(p.get('subtotal_linea') or 0)
    # descuento
    descuento_porcentaje = 0
    if usuario:
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT descuento_porcentaje FROM users WHERE usuario=%s", (usuario,))
            r = cursor.fetchone()
            if r:
                descuento_porcentaje = int(r[0] or 0)
        finally:
            try: cursor.close()
            except Exception: pass
    factor = Decimal(1) - (Decimal(descuento_porcentaje)/Decimal(100))
    total_con_descuento = (subtotal * factor).quantize(Decimal('1')) if subtotal else Decimal(0)
    payment_available = 'tbk.webpay_plus_create' in app.view_functions
    if not pedidos:
        return redirect(url_for('bp.inicio'))
    return render_template('carrito.html', pedidos=pedidos, usuario=usuario, descuento=descuento_porcentaje, total_con_descuento=total_con_descuento, subtotal=subtotal, payment_available=payment_available, cart_count=_get_cart_count())


@bp.route('/inicio')
def inicio():
    usuario = session.get('usuario')
    return render_template('inicio.html', tools=fetch_all_tools(), usuario=usuario, cart_count=_get_cart_count())

@bp.route('/Login') 
def login():
    return render_template('login.html', user=get_all_users(), cart_count=_get_cart_count())

@bp.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('bp.inicio'))

@bp.route('/Registro')
def registro():
    return render_template('registro.html', user=get_all_users(), cart_count=_get_cart_count())

# Rutas de categorías eliminadas: navegación ahora mediante anclas en /inicio



def error_page(error):
    return "PÁGINA NO ENCONTRADA..."
app.register_error_handler(404, error_page)


