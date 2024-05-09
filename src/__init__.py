from flask import Flask
from flask_mysqldb import MySQL
from config import appConfig

src = Flask(__name__)
src.config.from_object(appConfig)

mysql = MySQL(src)

from .routes import *
