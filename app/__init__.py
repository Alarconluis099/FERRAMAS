from flask import Flask, url_for, session
import uuid
from flask_mysqldb import MySQL
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:  # fallback si no está instalado (tests mínimos)
    Limiter = None  # type: ignore
    def get_remote_address():  # type: ignore
        return '127.0.0.1'
from config import get_config


def create_app():
    cfg_cls = get_config()
    app = Flask(__name__)
    app.config.from_object(cfg_cls)
    # Inicializa logging y otros hooks de config
    cfg_cls.init_app(app)
    return app


app = create_app()

limiter = None
if Limiter is not None:
    limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour", "50 per minute"])

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
        # Reinicio detectado: invalidar completamente la sesión (logout forzado)
        session.clear()
        session['_boot_id'] = current_boot

mysql = MySQL(app)

# --- Simple one-time migration: add 'role' column to users if absent ---
def _ensure_role_column():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SHOW COLUMNS FROM users LIKE 'role'")
        exists = cur.fetchone()
        if not exists:
            cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            mysql.connection.commit()
        cur.close()
    except Exception as e:
        # Non-fatal; just print warning
        print(f"[MIGRATION] Could not ensure role column: {e}")

def _ensure_transacciones_columns():
    """Garantiza columnas token, status y created_at en transacciones."""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SHOW COLUMNS FROM transacciones")
        cols = [r[0] for r in cur.fetchall()]
        altered = False
        if 'token' not in cols:
            cur.execute("ALTER TABLE transacciones ADD COLUMN token VARCHAR(128) NULL")
            altered = True
        if 'status' not in cols:
            cur.execute("ALTER TABLE transacciones ADD COLUMN status VARCHAR(32) NULL")
            altered = True
        if 'created_at' not in cols:
            cur.execute("ALTER TABLE transacciones ADD COLUMN created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP")
            altered = True
        if altered:
            mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"[MIGRATION] Could not ensure transacciones columns: {e}")

def _ensure_pedidos_snapshot_column():
    """Añade la columna total_items_final para snapshot de items al completar pedido."""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SHOW COLUMNS FROM pedidos LIKE 'total_items_final'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE pedidos ADD COLUMN total_items_final INT NULL")
            mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"[MIGRATION] Could not ensure pedidos.total_items_final: {e}")

def _backfill_total_items_final():
    """Rellena total_items_final donde sea NULL usando suma de pedido_detalle."""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE pedidos p
            LEFT JOIN (
                SELECT id_pedido, COALESCE(SUM(cantidad),0) AS cnt
                FROM pedido_detalle
                GROUP BY id_pedido
            ) d ON p.id = d.id_pedido
            SET p.total_items_final = d.cnt
            WHERE p.total_items_final IS NULL
        """)
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"[MIGRATION] Could not backfill total_items_final: {e}")

def _backfill_estado_pedido():
    """Marca como 'completado' pedidos con transacción AUTHORIZED si estado vacío."""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE pedidos p
            JOIN transacciones t ON t.id_pedido = p.id
            SET p.estado_pedido = 'completado'
            WHERE (p.estado_pedido IS NULL OR p.estado_pedido = '')
              AND t.status = 'AUTHORIZED'
        """)
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"[MIGRATION] Could not backfill estado_pedido: {e}")

try:
    # Ejecutar migraciones dentro de un app context
    with app.app_context():
        _ensure_role_column()
        _ensure_transacciones_columns()
        _ensure_pedidos_snapshot_column()
        _backfill_total_items_final()
        _backfill_estado_pedido()
except Exception as e:
    print(f"[MIGRATION] Deferred ensuring role/transacciones/pedidos columns: {e}")

# Exponer utilidad para forzar migración desde otros módulos si se inicializó antes
def ensure_role_column_again():
    _ensure_role_column()

from .routes import bp, attach_rate_limits
app.register_blueprint(bp)
try:
    attach_rate_limits()
except Exception:
    pass

# Endpoints de salud
@app.route('/health')
def health():
    return {'ok': True, 'status': 'healthy'}, 200

@app.route('/ready')
def ready():
    try:
        cur = mysql.connection.cursor(); cur.execute('SELECT 1'); cur.fetchone(); cur.close()
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return {'ok': db_ok, 'db': db_ok}, status

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

# Se evita construir URL en import-time para no romper tests.



