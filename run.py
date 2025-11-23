"""Punto de entrada de desarrollo.

Usa la aplicación creada en app/__init__.py. Si en el futuro se adopta un patrón factory,
este archivo puede modificarse para llamar create_app(config_name).
"""

from app import app  # noqa: E402

if __name__ == "__main__":
    # Permitir override de host/port vía variables de entorno.
    import os
    import logging
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    # Forzar logging a nivel INFO y modo debug para toda la app y Flask
    import sys
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    handler.setFormatter(formatter)
    # Elimina handlers previos para evitar duplicados
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(handler)
    # También para el logger de Flask y Werkzeug
    logging.getLogger('flask.app').setLevel(logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    app.run(host=host, port=port, debug=True)