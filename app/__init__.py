from flask import Flask
from flask_mysqldb import MySQL
from config import appConfig


import os

class appConfig():
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'ferramas'
    MYSQL_HOST = 'localhost'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'passwebpay777'


app = Flask(__name__)
app.config.from_object(appConfig)

mysql = MySQL(app)

from .routes import bp as routes_bp
app.register_blueprint(routes_bp)



