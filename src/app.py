from flask import Flask
from config import appConfig
from flask_mysqldb import MySQL

app = Flask (__name__)

mysql = MySQL(app)

@app.route('/Clientes')
def vista_clientes():
    try:
        return "OK"
    except Exception as e:
        return "Error" 

if __name__ == '__main__':
    app.config.from_object(appConfig)
    app.run()