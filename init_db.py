"""Script sencillo para inicializar base de datos desde schema.sql y seeds.sql.
Uso:
  python init_db.py  # requiere variables de conexión en .env
"""
import os
import MySQLdb
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv('MYSQL_USER','root')
DB_PASS = os.getenv('MYSQL_PASSWORD','')
DB_HOST = os.getenv('MYSQL_HOST','localhost')
DB_PORT = int(os.getenv('MYSQL_PORT','3306'))
DB_NAME = os.getenv('MYSQL_DB','ferramas')

def run_sql_file(cur, path):
    with open(path,'r',encoding='utf-8') as f:
        sql = f.read()
    for statement in [s.strip() for s in sql.split(';') if s.strip()]:
        cur.execute(statement)

def main():
    print(f"Conectando a {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    conn = MySQLdb.connect(user=DB_USER, passwd=DB_PASS, host=DB_HOST, port=DB_PORT, database=DB_NAME)
    cur = conn.cursor()
    base = os.path.dirname(__file__)
    schema = os.path.join(base,'schema.sql')
    seeds = os.path.join(base,'seeds.sql')
    if os.path.exists(schema):
        print('Aplicando schema.sql...')
        run_sql_file(cur, schema)
    if os.path.exists(seeds):
        print('Aplicando seeds.sql...')
        run_sql_file(cur, seeds)
    conn.commit()
    cur.close(); conn.close()
    print('Listo.')

if __name__ == '__main__':
    main()