import os

class appConfig():
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'ferramas'
    MYSQL_HOST = 'localhost'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'passwebpay777'

