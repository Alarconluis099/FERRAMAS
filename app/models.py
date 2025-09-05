from app import mysql
from flask import current_app
import MySQLdb
from MySQLdb.cursors import DictCursor
from datetime import datetime, timedelta

# --- Runtime detection of timestamp column in pedidos (created_at vs fecha_pedido) ---
_PEDIDOS_TS_COL = None  # caches actual column name if exists

def _detect_pedidos_timestamp():
    """Return the name of the timestamp column in pedidos (created_at or fecha_pedido) or None.
    Caches the result to avoid repeated SHOW COLUMNS.
    """
    global _PEDIDOS_TS_COL
    if _PEDIDOS_TS_COL is not None:
        return _PEDIDOS_TS_COL
    try:
        cur = mysql.connection.cursor()
        cur.execute("SHOW COLUMNS FROM pedidos")
        cols = [r[0] for r in cur.fetchall()]
        cur.close()
        if 'created_at' in cols:
            _PEDIDOS_TS_COL = 'created_at'
        elif 'fecha_pedido' in cols:
            _PEDIDOS_TS_COL = 'fecha_pedido'
        else:
            _PEDIDOS_TS_COL = None
    except Exception:
        _PEDIDOS_TS_COL = None
    return _PEDIDOS_TS_COL


"""Nota: Se eliminaron funciones legacy fetch_all_pedido*, fetch_pedido_by_id por no usarse.
Si se requieren en el futuro, restaurar desde historial git.
"""

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

def fetch_tools_filtered(page=1, per_page=12, q=None, precio_min=None, precio_max=None, order=None):
    """Return paginated & filtered tools plus total count.
    order accepted values: precio_asc, precio_desc, nombre_asc, nombre_desc, stock_asc, stock_desc
    Returns (items_list, total_count)
    """
    if page < 1: page = 1
    if per_page < 1: per_page = 12
    if per_page > 200: per_page = 200
    params = []
    where_clauses = []
    if q:
        where_clauses.append("(name LIKE %s OR description LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])
    if precio_min is not None:
        where_clauses.append("precio >= %s")
        params.append(precio_min)
    if precio_max is not None:
        where_clauses.append("precio <= %s")
        params.append(precio_max)
    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    order_map = {
        'precio_asc': 'precio ASC',
        'precio_desc': 'precio DESC',
        'nombre_asc': 'name ASC',
        'nombre_desc': 'name DESC',
        'stock_asc': 'stock ASC',
        'stock_desc': 'stock DESC'
    }
    order_sql = order_map.get(order, 'id_tool DESC')
    offset = (page - 1) * per_page
    cursor = mysql.connection.cursor(DictCursor)
    try:
        # Count total filtered
        cursor.execute(f"SELECT COUNT(*) AS c FROM tools{where_sql}", tuple(params))
        total = cursor.fetchone().get('c', 0)
        # Fetch page
        cursor.execute(
            f"SELECT id_tool, name, description, stock, precio FROM tools{where_sql} ORDER BY {order_sql} LIMIT %s OFFSET %s",
            tuple(params + [per_page, offset])
        )
        items = cursor.fetchall()
        return items, total
    except Exception as e:
        current_app.logger.error(f"Error fetching filtered tools: {e}")
        return [], 0
    finally:
        cursor.close()

def fetch_tool_suggestions(q, limit=8):
    """Return lightweight suggestions (id_tool, name, precio) for autocomplete."""
    if not q:
        return []
    like = f"%{q}%"
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute(
            "SELECT id_tool, name, precio FROM tools WHERE name LIKE %s OR description LIKE %s ORDER BY name ASC LIMIT %s",
            (like, like, limit)
        )
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        cursor.close()

# (Eliminado: fetch_pedido_by_id legacy)

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

def get_user_discount(usuario):
    """Devuelve el porcentaje de descuento vigente (int) para un usuario o 0 si no existe."""
    if not usuario:
        return 0
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT COALESCE(descuento_porcentaje,0) FROM users WHERE usuario=%s", (usuario,))
        row = cur.fetchone(); cur.close()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0

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
        # Calcular items antes de cerrar
        try:
            cursor.execute("SELECT COALESCE(SUM(cantidad),0) FROM pedido_detalle WHERE id_pedido=%s", (order_id,))
            items_total = cursor.fetchone()[0] or 0
        except Exception:
            items_total = 0
        # Detectar si existe columna total_items_final
        try:
            cursor.execute("SHOW COLUMNS FROM pedidos LIKE 'total_items_final'")
            has_col = cursor.fetchone() is not None
        except Exception:
            has_col = False
        if has_col:
            cursor.execute(
                "UPDATE pedidos SET monto_total=%s, estado_pedido='completado', total_items_final=%s WHERE id_pedido=%s",
                (total, items_total, order_id)
            )
        else:
            cursor.execute(
                "UPDATE pedidos SET monto_total=%s, estado_pedido='completado' WHERE id_pedido=%s",
                (total, order_id)
            )
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
        ts_col = _detect_pedidos_timestamp()
        # Detectar si existe snapshot de items final
        has_snapshot = False
        try:
            cursor.execute("SHOW COLUMNS FROM pedidos LIKE 'total_items_final'")
            has_snapshot = cursor.fetchone() is not None
        except Exception:
            has_snapshot = False
        # Build aggregate subquery to avoid ONLY_FULL_GROUP_BY issues
        base_agg = """
            SELECT id_pedido,
                   SUM(cantidad) AS total_items,
                   SUM(cantidad*precio_unitario) AS subtotal_calc
            FROM pedido_detalle
            GROUP BY id_pedido
        """
        ts_select = f", p.{ts_col} AS created_at" if ts_col else ""
        snapshot_select = ", p.total_items_final" if has_snapshot else ""
        try:
            cursor.execute(f"""
                SELECT p.id_pedido, p.id_user, u.usuario AS username, p.monto_total, p.estado_pedido{ts_select}{snapshot_select},
                       COALESCE(a.total_items,0) AS total_items,
                       COALESCE(a.subtotal_calc,0) AS subtotal_calc
                FROM pedidos p
                LEFT JOIN ({base_agg}) a ON a.id_pedido = p.id_pedido
                LEFT JOIN users u ON u.id_user = p.id_user
                ORDER BY p.id_pedido DESC
            """)
        except Exception:
            # Fallback sin join (no debería ocurrir, pero por seguridad)
            cursor.execute(f"""
                SELECT p.id_pedido, p.id_user, p.monto_total, p.estado_pedido{ts_select}{snapshot_select},
                       COALESCE(a.total_items,0) AS total_items,
                       COALESCE(a.subtotal_calc,0) AS subtotal_calc
                FROM pedidos p
                LEFT JOIN ({base_agg}) a ON a.id_pedido = p.id_pedido
                ORDER BY p.id_pedido DESC
            """)
        rows = cursor.fetchall()
        # If monto_total is NULL or 0 but estado finalized, use subtotal_calc
        for r in rows:
            if (r.get('monto_total') is None or r.get('monto_total') == 0) and r.get('subtotal_calc'):
                r['monto_total'] = r['subtotal_calc']
            # Si total_items = 0 (o None) pero hay snapshot, usarlo
            if has_snapshot and (r.get('total_items') in (0, None)) and r.get('total_items_final') not in (None, 0):
                r['total_items'] = r['total_items_final']
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
        ts_col = _detect_pedidos_timestamp()
        if ts_col:
            cursor.execute(f"""
                SELECT COALESCE(SUM(monto_total),0) AS total_monto,
                       COUNT(*) AS total_orders
                FROM pedidos
                WHERE estado_pedido='enviado' AND {ts_col} >= (NOW() - INTERVAL %s DAY)
            """, (days,))
        else:
            cursor.execute("""
                SELECT COALESCE(SUM(monto_total),0) AS total_monto,
                       COUNT(*) AS total_orders
                FROM pedidos
                WHERE estado_pedido='enviado'
            """)
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
        ts_col = _detect_pedidos_timestamp()
        if ts_col:
            cursor.execute(f"""
                SELECT d.id_tool, t.name, SUM(d.cantidad) AS unidades
                FROM pedido_detalle d
                JOIN pedidos p ON p.id_pedido=d.id_pedido
                JOIN tools t ON t.id_tool=d.id_tool
                WHERE p.estado_pedido='enviado' AND p.{ts_col} >= (NOW() - INTERVAL %s DAY)
                GROUP BY d.id_tool, t.name
                ORDER BY unidades DESC
                LIMIT %s
            """, (days, limit))
        else:
            cursor.execute("""
                SELECT d.id_tool, t.name, SUM(d.cantidad) AS unidades
                FROM pedido_detalle d
                JOIN pedidos p ON p.id_pedido=d.id_pedido
                JOIN tools t ON t.id_tool=d.id_tool
                WHERE p.estado_pedido='enviado'
                GROUP BY d.id_tool, t.name
                ORDER BY unidades DESC
                LIMIT %s
            """, (limit,))
        return cursor.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error top products: {e}")
        return []
    finally:
        cursor.close()

# Debug helper (not used in templates) to inspect pedidos rows directly
def _debug_fetch_pedidos_raw():
    cur = mysql.connection.cursor(DictCursor)
    try:
        cur.execute("SELECT * FROM pedidos ORDER BY id_pedido DESC LIMIT 50")
        return cur.fetchall()
    except Exception:
        return []
    finally:
        cur.close()

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