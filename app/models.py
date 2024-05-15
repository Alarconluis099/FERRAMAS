from app import mysql
from flask import current_app

def fetch_all_tools():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id, id_tools_type, name, description, stock FROM tools")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
        return data
    except Exception as e:
        current_app.logger.error(f"Error fetching tools: {e}")
        return []
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
    
