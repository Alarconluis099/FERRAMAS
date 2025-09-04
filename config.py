import os
from datetime import timedelta

class appConfig():
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'ferramas'
    MYSQL_HOST = 'localhost'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'passwebpay777'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

