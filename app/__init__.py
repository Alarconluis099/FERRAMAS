from flask import Flask
from flask_mysqldb import MySQL
from config import appConfig

app = Flask(__name__)
app.config.from_object(appConfig)

mysql = MySQL(app)

from .routes import *
