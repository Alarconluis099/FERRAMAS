import os
import logging
from datetime import timedelta
try:
    from dotenv import load_dotenv
except ImportError:  # fallback si no está instalado todavía
    def load_dotenv(*_, **__):
        return False

load_dotenv()  # intenta cargar .env si existe


class BaseConfig:
    # DB
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'ferramas')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    # App
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    RETURN_URL_TBK = os.getenv('RETURN_URL_TBK', 'http://localhost:5000/tbk/commit')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    # Seguridad cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    # Feature flags
    LEGACY_PLAIN_PASSWORD_ALLOWED = os.getenv('LEGACY_PLAIN_PASSWORD_ALLOWED', 'true').lower() == 'true'
    # Rate limiting (desactivar fácilmente en local)
    ENABLE_RATE_LIMITS = os.getenv('ENABLE_RATE_LIMITS', 'true').lower() == 'true'
    # Flask core flags (override en subclases)
    DEBUG = False
    TESTING = False

    @classmethod
    def init_app(cls, app):
        level = getattr(logging, cls.LOG_LEVEL, logging.INFO)
        if not app.logger.handlers:
            logging.basicConfig(level=level, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        else:
            app.logger.setLevel(level)
        app.logger.debug(f"Config cargada: {cls.__name__}")


class DevConfig(BaseConfig):
    DEBUG = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    LEGACY_PLAIN_PASSWORD_ALLOWED = True
    ENABLE_RATE_LIMITS = os.getenv('ENABLE_RATE_LIMITS', 'false').lower() == 'true'


class ProdConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # forzar secure en producción
    LEGACY_PLAIN_PASSWORD_ALLOWED = False


class TestConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    LEGACY_PLAIN_PASSWORD_ALLOWED = False
    # DB de test podría ser distinta (override si variable definida)
    MYSQL_DB = os.getenv('MYSQL_TEST_DB', BaseConfig.MYSQL_DB)


# Mantener compatibilidad con import previo (appConfig)
appConfig = DevConfig


def get_config():
    env = os.getenv('APP_ENV', 'dev').lower()
    if env in ('prod', 'production'):
        return ProdConfig
    if env in ('test', 'testing'):
        return TestConfig
    return DevConfig

