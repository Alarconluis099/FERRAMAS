from app import mysql
from flask import current_app

def fetch_all_pedido():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id_pedido, nom_pedido, desc_pedido, precio_pedido, cantidad, id_user FROM pedido")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        unique_ids = set()
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
        cursor.execute("""
            SELECT id_pedido, nom_pedido, desc_pedido, precio_pedido,
                   SUM(precio_pedido * cantidad) AS precio_total, 
                   SUM(cantidad) AS cantidad_total
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
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT DISTINCT id_tool, id_tools_type, name, description, stock, precio FROM tools")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]

        # Crear un conjunto para almacenar IDs únicos
        unique_ids = set()
        data = []
        for row in rows:
            tool_id = row[0]  # Obtener el ID de la herramienta
            if tool_id not in unique_ids:  # Verificar si el ID ya está en el conjunto
                unique_ids.add(tool_id)
                data.append(dict(zip(columns, row)))  # Agregar solo si es único

        return data
    except Exception as e:
        current_app.logger.error(f"Error fetching tools: {e}")
        return []
    finally:
        cursor.close()

def fetch_pedido_by_id(code):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(f"SELECT SUM(precio_pedido * cantidad) FROM pedido WHERE id_pedido = {code}")
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
        cursor.execute("SELECT * FROM tools WHERE code=%s", (code,))
        data = cursor.fetchone()
        return data
    except Exception as e:
        current_app.logger.error(f"Error fetching tool by code {code}: {e}")
        return None
    finally:
        cursor.close()

def insert_tools(tools_data):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("INSERT INTO tools (id, id_tools_type, name, description, stock) VALUES (%s, %s, %s, %s, %s)",
                       (tools_data['id'], tools_data['id_tools_type'], tools_data['name'], tools_data['description'], tools_data['stock']))
        mysql.connection.commit()
        return True
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error inserting tool: {e}")
        return False
    finally:
        cursor.close()


def delete_tools(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM tools WHERE id=%s", (id,))
        mysql.connection.commit()
        if cursor.rowcount > 0:
            return True
        else:
            return False
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error deleting tool by code {id}: {e}")
        return False
    finally:
        cursor.close()


def update_tools(id, tools_data):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(""" UPDATE tools SET id_tools_type=%s, name=%s, description=%s, stock=%s WHERE id=%s
                       """, (tools_data['id_tools_type'], tools_data['name'], tools_data['description'], tools_data['stock'], id))
        mysql.connection.commit()
        if cursor.rowcount > 0:
            return True
        else:
            return False
    except Exception as e:
        current_app.logger.error(f"Error updating tool by id {id}: {e}")
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


def fetch_users_by_id(id_users):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id_users, correo,  FROM users WHERE id_users = %s", (id_users,))  
        user_data = cursor.fetchone()

        if user_data:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, user_data))
        else:
            return {} 
    except mysql.connector.OperationalError as e:
        current_app.logger.error(f"Error de base de datos al obtener usuario por ID {id_users}: {e}")
        return {}
    finally:
        cursor.close()

def get_usuario_by_usuario(usuario):
    cursor = mysql.connection.cursor(dictionary=True)  # Para obtener resultados como diccionarios
    try:
        cursor.execute("SELECT correo, usuario FROM users WHERE usuario = %s", (usuario,))
        usuario_data = cursor.fetchone()

        # No incluimos la contraseña ni el hash de verificación en la respuesta
        if usuario_data:
            del usuario_data['contraseña'] 
            del usuario_data['verificar_contraseña']

        return usuario_data  
    except Exception as e:
        current_app.logger.error(f"Error de base de datos al obtener usuario: {e}")
        return None  
    finally:
        cursor.close()