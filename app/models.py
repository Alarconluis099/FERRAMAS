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
        cursor.execute("INSERT INTO tools (code, name, price, category) VALUES (%s, %s, %s, %s)",
                       (tools_data['code'], tools_data['name'], tools_data['price'], tools_data['category']))
        mysql.connection.commit()
        return True
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error(f"Error inserting tool: {e}")
        return False
    finally:
        cursor.close()
