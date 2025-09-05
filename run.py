"""Punto de entrada de desarrollo.

Usa la aplicación creada en app/__init__.py. Si en el futuro se adopta un patrón factory,
este archivo puede modificarse para llamar create_app(config_name).
"""

from app import app  # noqa: E402

if __name__ == "__main__":
    # Permitir override de host/port vía variables de entorno.
    import os

    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host=host, port=port, debug=debug)