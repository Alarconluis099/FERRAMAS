import os
from datetime import timedelta
try:
    from dotenv import load_dotenv
except ImportError:  # fallback si no está instalado todavía
    def load_dotenv(*_, **__):
        return False

load_dotenv()  # intenta cargar .env si existe

class appConfig:
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'ferramas')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

