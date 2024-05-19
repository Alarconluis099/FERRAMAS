from flask import Flask
from flask_mysqldb import MySQL
from config import appConfig
# from transbank.webpay.webpay_plus import WebpayPlus


app = Flask(__name__)
app.config.from_object(appConfig)

mysql = MySQL(app)

from .routes import *




