from app import mysql
from flask import current_app
import MySQLdb
from MySQLdb.cursors import DictCursor
from datetime import datetime, timedelta

"""Compatibilidad: funciones antiguas asociadas a la tabla 'pedido' (eliminada).
Se mantienen como no-op / retornos vacíos para no romper imports existentes.
"""

def fetch_all_pedido():  # legacy placeholder
    return []

def fetch_all_pedidos_ready():  # legacy placeholder
    return []

def fetch_all_tools():
    """Return all tools (schema sin id_tools_type)."""
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id_tool, name, description, stock, precio FROM tools")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        current_app.logger.error(f"Error fetching tools: {e}")
        return []
    finally:
        cursor.close()

def fetch_pedido_by_id(code):  # legacy placeholder
    return None

def fetch_tools_by_code(code):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT * FROM tools WHERE id_tool=%s", (code,))
        return cursor.fetchone()
    except Exception as e:
        current_app.logger.error(f"Error fetching tool by id_tool {code}: {e}")
        return None
    finally:
        cursor.close()

def insert_tools(tools_data):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO tools (id_tool, name, description, stock, precio)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            tools_data['id_tool'],
            tools_data['name'],
            tools_data.get('description'),
            tools_data.get('stock', 0),
            tools_data.get('precio', 0)
        ))
        mysql.connection.commit()
        return True
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error inserting tool: {e}")
        return False
    finally:
        cursor.close()


def delete_tools(id_tool):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM tools WHERE id_tool=%s", (id_tool,))
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error deleting tool by id_tool {id_tool}: {e}")
        return False
    finally:
        cursor.close()


def update_tools(id_tool, tools_data):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            UPDATE tools
            SET name=%s, description=%s, stock=%s, precio=%s
            WHERE id_tool=%s
        """, (
            tools_data['name'],
            tools_data.get('description'),
            tools_data.get('stock', 0),
            tools_data.get('precio', 0),
            id_tool
        ))
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        current_app.logger.error(f"Error updating tool by id_tool {id_tool}: {e}")
        return False
    finally:
        cursor.close()
    

def get_all_users():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        users = [dict(zip(columns, row)) for row in rows]

        return users  # Devolver lista de diccionarios

    except Exception as e:
        current_app.logger.error(f"Error de base de datos al obtener usuarios: {e}")
        return []
    finally:
        cursor.close()


def fetch_users_by_id(id_user):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id_user, correo, usuario, descuento FROM users WHERE id_user = %s", (id_user,))  
        user_data = cursor.fetchone()
        if user_data:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, user_data))
        return {}
    except Exception as e:
        current_app.logger.error(f"Error de base de datos al obtener usuario por ID {id_user}: {e}")
        return {}
    finally:
        cursor.close()

def get_usuario_by_usuario(usuario):
    """Return basic public info for a user (no password)."""
    try:
        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute("SELECT correo, usuario, descuento_porcentaje FROM users WHERE usuario = %s", (usuario,))
        return cursor.fetchone()
    except Exception as e:
        current_app.logger.error(f"Error de base de datos al obtener usuario: {e}")
        return None
    finally:
        try:
            cursor.close()
        except Exception:
            pass

# ==================== NUEVO ESQUEMA NORMALIZADO ====================

def get_user_open_order(user_id):
    """Return id_pedido for user open (estado_pedido='pendiente' and no pago registrado)."""
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id_pedido FROM pedidos WHERE id_user=%s AND estado_pedido='pendiente' ORDER BY id_pedido DESC LIMIT 1", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        cursor.close()

def create_order(user_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("INSERT INTO pedidos (id_user, estado_pedido, monto_total) VALUES (%s,'pendiente',0)", (user_id,))
        mysql.connection.commit()
        return cursor.lastrowid
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error creando pedido: {e}")
        return None
    finally:
        cursor.close()

def get_or_create_order(user_id):
    order_id = get_user_open_order(user_id)
    if order_id:
        return order_id
    return create_order(user_id)

def add_or_update_item(order_id, tool_id, quantity):
    """Add item or increase quantity. quantity is int to add."""
    cursor = mysql.connection.cursor()
    try:
        # Precio actual de la herramienta
        cursor.execute("SELECT precio, stock FROM tools WHERE id_tool=%s", (tool_id,))
        row = cursor.fetchone()
        if not row:
            return False
        precio, stock = row[0], row[1]
        if stock is not None and stock <= 0:
            return False  # sin stock
        cursor.execute("SELECT id_detalle, cantidad FROM pedido_detalle WHERE id_pedido=%s AND id_tool=%s", (order_id, tool_id))
        existing = cursor.fetchone()
        if existing:
            nueva = existing[1] + quantity
            # Validar stock
            if stock is not None and nueva > stock:
                return False
            if nueva <= 0:
                cursor.execute("DELETE FROM pedido_detalle WHERE id_detalle=%s", (existing[0],))
            else:
                cursor.execute("UPDATE pedido_detalle SET cantidad=%s WHERE id_detalle=%s", (nueva, existing[0]))
        else:
            if quantity > 0:
                if stock is not None and quantity > stock:
                    return False
                cursor.execute("INSERT INTO pedido_detalle (id_pedido, id_tool, cantidad, precio_unitario) VALUES (%s,%s,%s,%s)", (order_id, tool_id, quantity, precio))
        mysql.connection.commit()
        return True
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error agregando/actualizando item: {e}")
        return False
    finally:
        cursor.close()

def set_item_quantity(order_id, tool_id, new_qty):
    cursor = mysql.connection.cursor()
    try:
        if new_qty <= 0:
            cursor.execute("DELETE FROM pedido_detalle WHERE id_pedido=%s AND id_tool=%s", (order_id, tool_id))
        else:
            cursor.execute("SELECT id_detalle, cantidad FROM pedido_detalle WHERE id_pedido=%s AND id_tool=%s", (order_id, tool_id))
            row = cursor.fetchone()
            if row:
                # Validar stock
                cursor.execute("SELECT stock FROM tools WHERE id_tool=%s", (tool_id,))
                stock_row = cursor.fetchone()
                if stock_row and stock_row[0] is not None and new_qty > stock_row[0]:
                    return False
                cursor.execute("UPDATE pedido_detalle SET cantidad=%s WHERE id_detalle=%s", (new_qty, row[0]))
            else:
                cursor.execute("SELECT precio FROM tools WHERE id_tool=%s", (tool_id,))
                price_row = cursor.fetchone()
                if not price_row:
                    return False
                precio = price_row[0] or 0
                cursor.execute("SELECT stock FROM tools WHERE id_tool=%s", (tool_id,))
                srow = cursor.fetchone()
                if srow and srow[0] is not None and new_qty > srow[0]:
                    return False
                cursor.execute("INSERT INTO pedido_detalle (id_pedido,id_tool,cantidad,precio_unitario) VALUES (%s,%s,%s,%s)", (order_id, tool_id, new_qty, precio))
        mysql.connection.commit()
        return True
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error estableciendo cantidad item: {e}")
        return False
    finally:
        cursor.close()

def remove_item(order_id, tool_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM pedido_detalle WHERE id_pedido=%s AND id_tool=%s", (order_id, tool_id))
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error eliminando item: {e}")
        return False
    finally:
        cursor.close()

def get_cart_items(order_id):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("""
            SELECT d.id_tool, t.name, t.description, d.cantidad, d.precio_unitario,
                   (d.cantidad * d.precio_unitario) AS subtotal_linea
            FROM pedido_detalle d
            JOIN tools t ON t.id_tool = d.id_tool
            WHERE d.id_pedido=%s
            ORDER BY d.id_detalle DESC
        """, (order_id,))
        return cursor.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error obteniendo items del carrito: {e}")
        return []
    finally:
        cursor.close()

def get_cart_totals(order_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT COALESCE(SUM(cantidad*precio_unitario),0) FROM pedido_detalle WHERE id_pedido=%s", (order_id,))
        total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COALESCE(SUM(cantidad),0) FROM pedido_detalle WHERE id_pedido=%s", (order_id,))
        count = cursor.fetchone()[0] or 0
        return total, count
    except Exception as e:
        current_app.logger.error(f"Error obteniendo totales del carrito: {e}")
        return 0,0
    finally:
        cursor.close()

def clear_order_items(order_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM pedido_detalle WHERE id_pedido=%s", (order_id,))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error limpiando items de pedido {order_id}: {e}")
    finally:
        cursor.close()

def finalize_order(order_id, total):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE pedidos SET monto_total=%s, estado_pedido='enviado' WHERE id_pedido=%s", (total, order_id))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error finalizando pedido {order_id}: {e}")
    finally:
        cursor.close()

def insert_transaction(order_id, amount, metodo='Webpay Plus'):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("INSERT INTO transacciones (id_pedido, monto_transaccion, metodo_pago) VALUES (%s,%s,%s)", (order_id, amount, metodo))
        mysql.connection.commit()
        return True
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error registrando transaccion pedido {order_id}: {e}")
        return False
    finally:
        cursor.close()

# --- Admin / reporting helpers ---
def fetch_all_orders():
    """Return list of pedidos with computed totals and item counts."""
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("""
            SELECT p.id_pedido, p.id_user, p.monto_total, p.estado_pedido, p.created_at,
                   COALESCE(SUM(d.cantidad),0) AS total_items,
                   COALESCE(SUM(d.cantidad*d.precio_unitario),0) AS subtotal_calc
            FROM pedidos p
            LEFT JOIN pedido_detalle d ON d.id_pedido = p.id_pedido
            GROUP BY p.id_pedido
            ORDER BY p.id_pedido DESC
        """)
        rows = cursor.fetchall()
        # If monto_total is NULL or 0 but estado finalized, use subtotal_calc
        for r in rows:
            if (r.get('monto_total') is None or r.get('monto_total') == 0) and r.get('subtotal_calc'):
                r['monto_total'] = r['subtotal_calc']
        return rows
    except Exception as e:
        current_app.logger.error(f"Error fetching orders: {e}")
        return []
    finally:
        cursor.close()

def fetch_order_detail(order_id):
    """Return header + items for one pedido."""
    cur = mysql.connection.cursor(DictCursor)
    try:
        cur.execute("SELECT * FROM pedidos WHERE id_pedido=%s", (order_id,))
        header = cur.fetchone()
        cur.execute("""
            SELECT d.id_detalle, d.id_tool, t.name, t.description, d.cantidad, d.precio_unitario,
                   (d.cantidad*d.precio_unitario) AS subtotal_linea
            FROM pedido_detalle d
            JOIN tools t ON t.id_tool=d.id_tool
            WHERE d.id_pedido=%s
            ORDER BY d.id_detalle ASC
        """, (order_id,))
        items = cur.fetchall()
        return header, items
    except Exception as e:
        current_app.logger.error(f"Error fetching order detail {order_id}: {e}")
        return None, []
    finally:
        cur.close()

def fetch_sales_metrics(days=7):
    """Return aggregate sales metrics for the last N days (estado_pedido='enviado')."""
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT COALESCE(SUM(monto_total),0) AS total_monto,
                   COUNT(*) AS total_orders
            FROM pedidos
            WHERE estado_pedido='enviado' AND created_at >= (NOW() - INTERVAL %s DAY)
        """, (days,))
        row = cursor.fetchone()
        total_monto = row[0] if row else 0
        total_orders = row[1] if row else 0
        return {
            'days': days,
            'total_monto': total_monto,
            'total_orders': total_orders
        }
    except Exception as e:
        current_app.logger.error(f"Error metrics: {e}")
        return {'days':days,'total_monto':0,'total_orders':0}
    finally:
        cursor.close()

def fetch_top_products(limit=5, days=30):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("""
            SELECT d.id_tool, t.name, SUM(d.cantidad) AS unidades
            FROM pedido_detalle d
            JOIN pedidos p ON p.id_pedido=d.id_pedido
            JOIN tools t ON t.id_tool=d.id_tool
            WHERE p.estado_pedido='enviado' AND p.created_at >= (NOW() - INTERVAL %s DAY)
            GROUP BY d.id_tool, t.name
            ORDER BY unidades DESC
            LIMIT %s
        """, (days, limit))
        return cursor.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error top products: {e}")
        return []
    finally:
        cursor.close()

def update_order_status(order_id, new_status):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE pedidos SET estado_pedido=%s WHERE id_pedido=%s", (new_status, order_id))
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error updating status pedido {order_id}: {e}")
        return False
    finally:
        cursor.close()