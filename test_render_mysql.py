import os
import MySQLdb

def test_render_mysql():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('DATABASE_URL no está definida')
        return
    import re
    # Acepta mysql://usuario:contraseña@host:puerto/db y mysql://usuario@host:puerto/db
    m = re.match(r'mysql://([^:]+)(?::([^@]*))?@([^:/]+)(?::(\d+))?/([^?]+)', db_url)
    if not m:
        print('DATABASE_URL mal formada')
        return
    user = m.group(1)
    password = m.group(2) if m.group(2) is not None else ''
    host = m.group(3)
    port = int(m.group(4) or 3306)
    db = m.group(5)
    try:
        conn = MySQLdb.connect(host=host, user=user, passwd=password, db=db, port=port)
        cur = conn.cursor()
        cur.execute('SELECT 1')
        print('Conexión exitosa a MySQL en Render')
        cur.close()
        conn.close()
    except Exception as e:
        print(f'Error de conexión: {e}')

if __name__ == '__main__':
    test_render_mysql()
