from app import mysql
from flask import current_app
import MySQLdb
from MySQLdb.cursors import DictCursor

def fetch_all_pedido():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id_pedido, nom_pedido, desc_pedido, precio_pedido, cantidad, id_user FROM pedido")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
        return data
    except Exception as e:
        current_app.logger.error(f"Error fetching pedido: {e}")
        return []
    finally:
        cursor.close()

def fetch_all_pedidos_ready():
    cursor = mysql.connection.cursor()
    try:
        # Use aggregate functions on non-grouped columns for compatibility with ONLY_FULL_GROUP_BY
        cursor.execute("""
            SELECT 
                id_pedido,
                MIN(nom_pedido)       AS nom_pedido,
                MIN(desc_pedido)      AS desc_pedido,
                MIN(precio_pedido)    AS precio_pedido,
                SUM(precio_pedido * cantidad) AS precio_total,
                SUM(cantidad)         AS cantidad_total
            FROM pedido
            GROUP BY id_pedido
        """)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]

        data = [dict(zip(columns, row)) for row in rows]
        return data
    except Exception as e:
        current_app.logger.error(f"Error fetching pedidos: {e}")
        return []
    finally:
        cursor.close()

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

def fetch_pedido_by_id(code):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT SUM(precio_pedido * cantidad) AS total FROM pedido WHERE id_pedido = %s", (code,))
        data = cursor.fetchone()
        return data
    except Exception as e:
        current_app.logger.error(f"Error fetching pedido by id: {e}")
        return None
    finally:
        cursor.close()

def fetch_tools_by_code(code):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM tools WHERE id_tool=%s", (code,))
        data = cursor.fetchone()
        return data
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
        cursor.execute("SELECT correo, usuario, descuento FROM users WHERE usuario = %s", (usuario,))
        return cursor.fetchone()
    except Exception as e:
        current_app.logger.error(f"Error de base de datos al obtener usuario: {e}")
        return None
    finally:
        try:
            cursor.close()
        except Exception:
            pass