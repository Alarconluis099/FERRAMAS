from flask import flash, request, Blueprint, jsonify, render_template, redirect, url_for, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from app import app
from .models import (
    fetch_all_tools,
    fetch_tools_by_code,
    fetch_tools_filtered,
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
    fetch_all_orders,
    fetch_order_detail,
    fetch_sales_metrics,
    fetch_top_products,
    update_order_status,
    _debug_fetch_pedidos_raw,
)
from . import mysql
import random


bp = Blueprint('bp', __name__)

# --- Admin utilities ---
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = session.get('usuario')
        if not user:
            flash('Acceso restringido.', 'error')
            return redirect(url_for('bp.inicio'))
        # Revisa role si existe
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT role FROM users WHERE usuario=%s", (user,))
            row = cur.fetchone()
            cur.close()
            role = row[0] if row else None
        except Exception:
            role = None
        # Compatibilidad: si el username es literalmente 'admin', concédelo aunque rol aún no migrado
        if role != 'admin' and user != 'admin':
            flash('Acceso restringido.', 'error')
            return redirect(url_for('bp.inicio'))
        return f(*args, **kwargs)
    return wrapper

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
    # Si no hay ningún admin aún, el primer usuario con nombre 'admin' será admin
    role = 'user'
    if username.lower() == 'admin':
        try:
            cur2 = mysql.connection.cursor()
            cur2.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
            if (cur2.fetchone() or [0])[0] == 0:
                role = 'admin'
            cur2.close()
        except Exception:
            pass
    try:
        cursor.execute(
            "INSERT INTO users (correo, contraseña, usuario, descuento_porcentaje, role) VALUES (%s,%s,%s,%s,%s)",
            (correo, hashed, username, 15, role)
        )
    except Exception as e:
        # Si la columna role no existe aún (migración falló), intenta sin esa columna
        if 'Unknown column' in str(e) and "'role'" in str(e):
            cursor.execute(
                "INSERT INTO users (correo, contraseña, usuario, descuento_porcentaje) VALUES (%s,%s,%s,%s)",
                (correo, hashed, username, 15)
            )
        else:
            cursor.close()
            flash('Error creando usuario.', 'error')
            return redirect(url_for('bp.registro'))
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
        try:
            cursor.execute(
                "SELECT id_user, usuario, contraseña, COALESCE(descuento_porcentaje,0), COALESCE(role,'') FROM users WHERE correo = %s",
                (correo_normalizado,)
            )
            result = cursor.fetchone()
            role_indexed = True
        except Exception as e:
            # Fallback si aún no existe la columna 'role'
            if 'Unknown column' in str(e) and "'role'" in str(e):
                cursor.execute(
                    "SELECT id_user, usuario, contraseña, COALESCE(descuento_porcentaje,0) FROM users WHERE correo = %s",
                    (correo_normalizado,)
                )
                row = cursor.fetchone()
                if row:
                    # Simular tupla con role vacío
                    result = (*row, '')
                else:
                    result = None
                role_indexed = False
            else:
                cursor.close()
                flash('Error en autenticación.', 'error')
                return redirect(url_for('bp.iniciar_sesion'))
        if not result:
            cursor.close()
            flash('Correo y/o contraseña inválidos.', 'error')
            return redirect(url_for('bp.iniciar_sesion'))

        usuario_id, usuario_nombre, stored_pass, descuento_pct, role = result

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

    # Auto-promoción desactivada para evitar logins inesperados como admin tras flujos externos.
    # if usuario_nombre == 'admin' and role != 'admin': ...
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
    # Paginación tradicional con control de "items por página".
    all_tools = fetch_all_tools()
    total = len(all_tools)
    # Leer per_page desde query (fallback 12) y sanitizar
    try:
        per_page = int(request.args.get('per_page', 12))
    except ValueError:
        per_page = 12
    allowed_opts = [12,20,40,80]
    if per_page not in allowed_opts:
        # normaliza al más cercano inferior existente
        per_page = max([o for o in allowed_opts if o <= per_page] or [12])
    page = 1  # inicial siempre 1 en render SSR; navegación posterior con JS
    initial = all_tools[:per_page]
    has_more = total > per_page
    return render_template(
        'inicio.html',
        tools=initial,
        total_tools=total,
        per_page=per_page,
        page=page,
        allowed_per_page=allowed_opts,
        has_more=has_more,
        usuario=usuario,
        cart_count=_get_cart_count()
    )

@bp.route('/api/tools')
def api_tools_paginated():
    # Filtros: q (texto), precio_min, precio_max, order
    try:
        page = int(request.args.get('page','1'))
        per_page = int(request.args.get('per_page','20'))
    except ValueError:
        return jsonify({'ok':False,'error':'Parámetros inválidos'}), 400
    q = request.args.get('q') or None
    order = request.args.get('order') or None
    def parse_int_or_none(key):
        v = request.args.get(key)
        if v is None or v == '':
            return None
        try:
            return int(v)
        except ValueError:
            return None
    precio_min = parse_int_or_none('precio_min')
    precio_max = parse_int_or_none('precio_max')
    items, total = fetch_tools_filtered(page=page, per_page=per_page, q=q, precio_min=precio_min, precio_max=precio_max, order=order)
    has_more = page * per_page < total
    return jsonify({'ok':True,'page':page,'per_page':per_page,'total':total,'has_more':has_more,'items':items})

@bp.route('/admin')
@admin_required
def admin_dashboard():
    """Panel sencillo: listado de productos y usuarios, con acciones básicas."""
    tools = fetch_all_tools()
    users = get_all_users()
    # Detectar stock bajo
    low_stock = [t for t in tools if (t.get('stock') or 0) <= 5]
    recent_orders = fetch_all_orders()[:10]
    metrics7 = fetch_sales_metrics(7)
    top_products = fetch_top_products()
    return render_template('admin_dashboard.html', tools=tools, users=users, low_stock=low_stock, recent_orders=recent_orders, metrics7=metrics7, top_products=top_products, usuario=session.get('usuario'), cart_count=_get_cart_count())

@bp.route('/admin/debug/schema')
@admin_required
def admin_debug_schema():
    info = {}
    try:
        cur = mysql.connection.cursor()
        cur.execute("SHOW COLUMNS FROM users")
        info['users_columns'] = [row[0] for row in cur.fetchall()]
        cur.execute("SHOW COLUMNS FROM pedidos")
        info['pedidos_columns'] = [row[0] for row in cur.fetchall()]
        cur.close()
    except Exception as e:
        info['error'] = str(e)
    return jsonify(info)

@bp.route('/admin/debug/pedidos')
@admin_required
def admin_debug_pedidos():
    return jsonify(_debug_fetch_pedidos_raw())

@bp.route('/admin/pedidos')
@admin_required
def admin_orders():
    orders = fetch_all_orders()
    return render_template('admin_orders.html', orders=orders, usuario=session.get('usuario'), cart_count=_get_cart_count())

@bp.route('/admin/pedidos/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    header, items = fetch_order_detail(order_id)
    if not header:
        flash('Pedido no encontrado', 'error')
        return redirect(url_for('bp.admin_orders'))
    total_calc = sum([(it.get('cantidad') or 0) * (it.get('precio_unitario') or 0) for it in items])
    # Maintain old keys (pedido) for backward compatibility if any fragment still references it
    return render_template('admin_order_detail.html', order=header, pedido=header, items=items, total_calc=total_calc, usuario=session.get('usuario'), cart_count=_get_cart_count())

@bp.route('/admin/pedidos/<int:order_id>/estado', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    new_status = request.form.get('estado')
    # Expand valid statuses aligned with new template options
    valid = {'pendiente','procesando','enviado','completado','cancelado'}
    if new_status not in valid:
        flash('Estado inválido', 'error')
        return redirect(url_for('bp.admin_order_detail', order_id=order_id))
    if update_order_status(order_id, new_status):
        flash('Estado actualizado', 'success')
    else:
        flash('No se pudo actualizar', 'error')
    return redirect(url_for('bp.admin_order_detail', order_id=order_id))

@bp.route('/admin/producto', methods=['POST'])
@admin_required
def admin_create_product():
    form = request.form
    try:
        name = form.get('name','').strip()
        precio = int(form.get('precio','0') or 0)
        stock = int(form.get('stock','0') or 0)
        desc = form.get('description')
        if not name:
            flash('Nombre requerido', 'error')
            return redirect(url_for('bp.admin_dashboard'))
        # Generar id_tool random que no choque
        cur = mysql.connection.cursor()
        import random
        for _ in range(5):
            candidate = random.randint(1000,999999)
            cur.execute("SELECT 1 FROM tools WHERE id_tool=%s", (candidate,))
            if not cur.fetchone():
                id_tool = candidate
                break
        else:
            cur.close()
            flash('No se pudo generar ID producto', 'error')
            return redirect(url_for('bp.admin_dashboard'))
        cur.execute("INSERT INTO tools (id_tool,name,description,stock,precio) VALUES (%s,%s,%s,%s,%s)", (id_tool,name,desc,stock,precio))
        mysql.connection.commit()
        cur.close()
        flash('Producto creado', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('Error creando producto', 'error')
    return redirect(url_for('bp.admin_dashboard'))

@bp.route('/admin/producto/<int:tool_id>', methods=['POST'])
@admin_required
def admin_update_product(tool_id):
    form = request.form
    action = form.get('_action')
    if action == 'delete':
        if delete_tools(tool_id):
            flash('Producto eliminado', 'info')
        else:
            flash('No se pudo eliminar', 'error')
        return redirect(url_for('bp.admin_dashboard'))
    try:
        name = form.get('name','').strip()
        desc = form.get('description')
        stock = int(form.get('stock','0') or 0)
        precio = int(form.get('precio','0') or 0)
        if not name:
            flash('Nombre requerido', 'error')
            return redirect(url_for('bp.admin_dashboard'))
        update_tools(tool_id, {'name':name,'description':desc,'stock':stock,'precio':precio})
        flash('Producto actualizado', 'success')
    except Exception:
        flash('Error actualizando producto', 'error')
    return redirect(url_for('bp.admin_dashboard'))

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


