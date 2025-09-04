from flask import Flask, url_for, session
import uuid
from flask_mysqldb import MySQL
from config import appConfig


app = Flask(__name__)
app.config.from_object(appConfig)

# Genera un identificador único por arranque del servidor para invalidar sesiones previas
BOOT_ID = uuid.uuid4().hex
app.config['SESSION_BOOT_ID'] = BOOT_ID

@app.before_request
def enforce_session_boot_id():
    """Mantiene control de reinicios sin cerrar la sesión del usuario.

    Antes: se hacía logout (session.clear) cuando el servidor reiniciaba, lo cual
    provocaba que al volver desde el flujo de pago (redirect de Transbank) el
    usuario apareciera deslogueado si ocurrió un auto-reload (debug) entre create y commit.

    Ahora: migramos suavemente la sesión preservando 'usuario'. Si se requiere la
    política estricta anterior, podría activarse con una variable de entorno en el futuro.
    """
    stored = session.get('_boot_id')
    current_boot = app.config['SESSION_BOOT_ID']
    if stored is None:
        session['_boot_id'] = current_boot
        return
    if stored != current_boot:
        # Guardar claves esenciales antes de limpiar (solo las que usamos realmente)
        preserved_usuario = session.get('usuario')
        # Limpiar solo metadatos no esenciales manteniendo usuario
        session.clear()
        session['_boot_id'] = current_boot
        if preserved_usuario:
            session['usuario'] = preserved_usuario

mysql = MySQL(app)

from .routes import bp
app.register_blueprint(bp)

_TBK_REGISTERED = False
try:
    from transbank_api.transbank_services import bp_tbk
    app.register_blueprint(bp_tbk, url_prefix='/tbk')
    _TBK_REGISTERED = True
except Exception as e:
    print(f"Warning: could not register Transbank blueprint: {e}")

if not _TBK_REGISTERED:
    @app.route('/tbk/create', methods=['POST'])
    def _tbk_missing_create():
        return {'error': 'Transbank no disponible'}, 503

with app.test_request_context():
    print(url_for('bp.inicio'))



