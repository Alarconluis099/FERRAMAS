from flask import Flask, url_for
from flask_mysqldb import MySQL
from config import appConfig


app = Flask(__name__)
app.config.from_object(appConfig)

mysql = MySQL(app)

from .routes import bp
app.register_blueprint(bp)

with app.test_request_context():
    print(url_for('bp.inicio'))



