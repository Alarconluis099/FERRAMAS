from flask import Blueprint, render_template, session, jsonify, current_app, request, redirect, url_for, flash
from .auth import role_required, admin_required, staff_or_admin_required
from app.models import (
    fetch_all_tools, get_all_users, fetch_all_orders, fetch_sales_metrics,
    fetch_top_products, fetch_order_detail, update_order_status, _debug_fetch_pedidos_raw
)

# Acceso diferido a mysql para permitir monkeypatch en tests (evita OperationalError 2006)
def _mysql():  # siempre devuelve objeto mysql (real o parcheado)
    try:
        from app.routes import mysql as patched  # type: ignore
        return patched
    except Exception:  # pragma: no cover - fallback
        from app import mysql as real  # type: ignore
        return real

admin_bp = Blueprint('admin', __name__)

# Helpers locales

def _get_cart_count():
    # Simplificado: no cargar items (se podría extraer a util compartido)
    return 0

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    tools = fetch_all_tools(); users = get_all_users()
    low_stock = [t for t in tools if (t.get('stock') or 0) <= 5]
    recent_orders = fetch_all_orders()[:10]
    metrics7 = fetch_sales_metrics(7); top_products = fetch_top_products()
    return render_template('admin_dashboard.html', tools=tools, users=users, low_stock=low_stock, recent_orders=recent_orders, metrics7=metrics7, top_products=top_products, usuario=session.get('usuario'), cart_count=_get_cart_count())

@admin_bp.route('/admin/debug/schema')
@admin_required
def admin_debug_schema():
    info = {}
    try:
        cur = _mysql().connection.cursor()
        cur.execute("SHOW COLUMNS FROM users")
        info['users_columns'] = [r[0] for r in cur.fetchall()]
        cur.execute("SHOW COLUMNS FROM pedidos")
        info['pedidos_columns'] = [r[0] for r in cur.fetchall()]
        cur.close()
    except Exception as e:
        info['error'] = str(e)
    return jsonify(info)

@admin_bp.route('/admin/debug/pedidos')
@admin_required
def admin_debug_pedidos(): return jsonify(_debug_fetch_pedidos_raw())

@admin_bp.route('/admin/transacciones')
@admin_required
def admin_transacciones():
    try:
        cur = _mysql().connection.cursor()
        cur.execute("SHOW COLUMNS FROM transacciones"); cols_all = [r[0] for r in cur.fetchall()]
        base_cols = ['id_transaccion','id_pedido','monto_transaccion','metodo_pago']
        base_cols.append("COALESCE(status,'') as status" if 'status' in cols_all else "'' as status")
        base_cols.append('token' if 'token' in cols_all else 'NULL as token')
        base_cols.append('created_at' if 'created_at' in cols_all else 'NULL as created_at')
        select_sql = ', '.join(base_cols)
        cur.execute(f"SELECT {select_sql} FROM transacciones ORDER BY id_transaccion DESC LIMIT 200")
        rows = cur.fetchall(); cols = [d[0] for d in cur.description]
        cur.close(); data = [dict(zip(cols,r)) for r in rows]
    except Exception as e:
        current_app.logger.error(f"Error listando transacciones: {e}")
        data = []
    return jsonify({'ok':True,'items':data})

@admin_bp.route('/admin/transacciones/vista')
@admin_required
def admin_transacciones_html():
    try:
        cur = _mysql().connection.cursor()
        cur.execute("SHOW COLUMNS FROM transacciones"); cols_all = [r[0] for r in cur.fetchall()]
        base_cols = ['id_transaccion','id_pedido','monto_transaccion','metodo_pago']
        base_cols.append("COALESCE(status,'') as status" if 'status' in cols_all else "'' as status")
        base_cols.append('token' if 'token' in cols_all else 'NULL as token')
        base_cols.append('created_at' if 'created_at' in cols_all else 'NULL as created_at')
        select_sql = ', '.join(base_cols)
        cur.execute(f"SELECT {select_sql} FROM transacciones ORDER BY id_transaccion DESC LIMIT 200")
        rows = cur.fetchall(); cols = [d[0] for d in cur.description]
        cur.close(); transacciones = [dict(zip(cols,r)) for r in rows]
    except Exception as e:
        current_app.logger.error(f"Error listando transacciones (html): {e}")
        transacciones = []
    return render_template('admin_transacciones.html', transacciones=transacciones, usuario=session.get('usuario'), cart_count=_get_cart_count())

@admin_bp.route('/admin/pedidos')
@admin_required
def admin_orders():
    orders = fetch_all_orders(); return render_template('admin_orders.html', orders=orders, usuario=session.get('usuario'), cart_count=_get_cart_count())

@admin_bp.route('/admin/pedidos/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    header, items = fetch_order_detail(order_id)
    if not header: flash('Pedido no encontrado', 'error'); return redirect(url_for('bp.admin_orders'))
    total_calc = sum([(it.get('cantidad') or 0)*(it.get('precio_unitario') or 0) for it in items])
    return render_template('admin_order_detail.html', order=header, pedido=header, items=items, total_calc=total_calc, usuario=session.get('usuario'), cart_count=_get_cart_count())

VALID_ORDER_STATUSES = {'pendiente','procesando','enviado','completado','cancelado'}

@admin_bp.route('/admin/pedidos/<int:order_id>/estado', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    new_status = request.form.get('estado')
    if new_status not in VALID_ORDER_STATUSES:
        flash('Estado inválido', 'error'); return redirect(url_for('bp.admin_order_detail', order_id=order_id))
    if update_order_status(order_id, new_status): flash('Estado actualizado', 'success')
    else: flash('No se pudo actualizar', 'error')
    return redirect(url_for('bp.admin_order_detail', order_id=order_id))

@admin_bp.route('/admin/producto', methods=['POST'])
@staff_or_admin_required
def admin_create_product():
    form = request.form
    try:
        name = form.get('name','').strip(); precio = int(form.get('precio','0') or 0); stock = int(form.get('stock','0') or 0); desc = form.get('description')
        if not name:
            flash('Nombre requerido', 'error'); return redirect(url_for('bp.admin_dashboard'))
        import random
        cur = _mysql().connection.cursor()
        for _ in range(5):
            candidate = random.randint(1000,999999)
            cur.execute("SELECT 1 FROM tools WHERE id_tool=%s", (candidate,))
            if not cur.fetchone():
                id_tool = candidate
                break
        else:
            cur.close(); flash('No se pudo generar ID producto', 'error'); return redirect(url_for('bp.admin_dashboard'))
        cur.execute("INSERT INTO tools (id_tool,name,description,stock,precio) VALUES (%s,%s,%s,%s,%s)", (id_tool,name,desc,stock,precio))
        _mysql().connection.commit(); cur.close(); flash('Producto creado', 'success')
    except Exception:
        _mysql().connection.rollback(); flash('Error creando producto', 'error')
    return redirect(url_for('bp.admin_dashboard'))

@admin_bp.route('/admin/producto/<int:tool_id>', methods=['POST'])
@staff_or_admin_required
def admin_update_product(tool_id):
    form = request.form; action = form.get('_action')
    if action == 'delete':
        from app.models import delete_tools
        if delete_tools(tool_id): flash('Producto eliminado', 'info')
        else: flash('No se pudo eliminar', 'error')
        return redirect(url_for('bp.admin_dashboard'))
    try:
        from app.models import update_tools
        name = form.get('name','').strip(); desc = form.get('description'); stock = int(form.get('stock','0') or 0); precio = int(form.get('precio','0') or 0)
        if not name: flash('Nombre requerido', 'error'); return redirect(url_for('bp.admin_dashboard'))
        update_tools(tool_id, {'name':name,'description':desc,'stock':stock,'precio':precio}); flash('Producto actualizado', 'success')
    except Exception:
        flash('Error actualizando producto', 'error')
    return redirect(url_for('bp.admin_dashboard'))

@admin_bp.route('/admin/usuario/<int:user_id>/rol', methods=['POST'])
@admin_required
def admin_update_user_role(user_id):
    role = (request.form.get('role') or 'user').strip().lower(); descuento = request.form.get('descuento') or ''
    if role not in ('user','staff','admin'): flash('Rol inválido', 'error'); return redirect(url_for('bp.admin_dashboard'))
    try:
        d = int(descuento)
        if d < 0 or d > 100: raise ValueError
    except ValueError:
        flash('Descuento inválido', 'error'); return redirect(url_for('bp.admin_dashboard'))
    try:
        cur = _mysql().connection.cursor()
        cur.execute("SELECT usuario FROM users WHERE id_user=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            flash('Usuario no encontrado', 'error'); cur.close(); return redirect(url_for('bp.admin_dashboard'))
        username = row[0]
        if username == 'admin' and role != 'admin':
            flash('No se puede cambiar rol del admin principal', 'error'); cur.close(); return redirect(url_for('bp.admin_dashboard'))
        cur.execute("UPDATE users SET role=%s, descuento_porcentaje=%s WHERE id_user=%s", (role, d, user_id))
        _mysql().connection.commit(); cur.close(); flash('Usuario actualizado', 'success')
    except Exception as e:
        current_app.logger.error(f"Error actualizando rol usuario {user_id}: {e}")
        _mysql().connection.rollback(); flash('Error actualizando usuario', 'error')
    return redirect(url_for('bp.admin_dashboard'))

@admin_bp.route('/staff')
@role_required('admin','staff')
def staff_dashboard():
    tools = fetch_all_tools(); low_stock = [t for t in tools if (t.get('stock') or 0) <= 5]
    return render_template('staff_dashboard.html', tools=tools, low_stock=low_stock, usuario=session.get('usuario'), cart_count=_get_cart_count())
