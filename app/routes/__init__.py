"""Paquete de blueprints separados.
Importa y registra cada subconjunto desde create_app si se desea.
Por compatibilidad mantenemos el blueprint 'bp' agregando sub-blueprints.
"""
from flask import Blueprint, render_template, session, request, redirect, url_for
from app.models import fetch_all_tools

bp = Blueprint('bp', __name__)

# Sub‑blueprints se importan abajo para adjuntar rutas
from .auth import auth_bp  # noqa: E402
from .cart import cart_bp  # noqa: E402
from .admin import admin_bp  # noqa: E402
from .api import api_bp  # noqa: E402

# Registrar sub-blueprints con prefijos según necesidad (aquí sin prefijo para preservar URLs)
bp.register_blueprint(auth_bp)
bp.register_blueprint(cart_bp)
bp.register_blueprint(admin_bp)
bp.register_blueprint(api_bp)

# Alias de endpoints (plantillas legacy esperan bp.api_tools_paginated y bp.api_guardar_pedido)
try:
	from .api import api_tools_paginated as _api_tools_fn  # type: ignore
	bp.add_url_rule('/api/tools', endpoint='api_tools_paginated', view_func=_api_tools_fn)
except Exception:
	pass
try:
	from .cart import api_guardar_pedido as _api_add_fn  # type: ignore
	bp.add_url_rule('/api/guardar_pedido', endpoint='api_guardar_pedido', view_func=_api_add_fn, methods=['POST'])
except Exception:
	pass
try:
	from .api import api_tool_suggestions as _api_sugg_fn  # type: ignore
	bp.add_url_rule('/api/tool_suggestions', endpoint='api_tool_suggestions', view_func=_api_sugg_fn)
except Exception:
	pass

# Exponer helper para rate limits más adelante
from .rate_limits import attach_rate_limits  # noqa: E402

# Ruta principal '/inicio' mantenida para compatibilidad con código legacy
@bp.route('/inicio')
def inicio():
	usuario = session.get('usuario')
	# Parámetros simples de búsqueda inicial
	query = (request.args.get('q') or '').strip().lower()
	tools = fetch_all_tools()
	if query:
		tools = [t for t in tools if query in (t.get('name','').lower()) or query in (t.get('description','') or '').lower()]
	# Limitar a primeros 12 (paginación real ahora via /api/tools)
	return render_template('inicio.html', tools=tools[:12], total_tools=len(tools), per_page=12, page=1, allowed_per_page=[12,20,40,80], has_more=len(tools)>12, usuario=usuario, search_query=query, cart_count=0)

# Ruta raíz para evitar 404 cuando se entra a http://host:puerto/
@bp.route('/')
def root_index():
	return redirect(url_for('bp.inicio'))

# --- Alias para mantener endpoint 'bp.iniciar_sesion' que usaban tests legacy ---
@bp.route('/iniciar_sesion', methods=['GET','POST'])
def iniciar_sesion():
	from .auth import iniciar_sesion as _inner
	return _inner()

# Aliases legacy para templates
@bp.route('/Login')
def login():
	from .auth import login_alias as _login
	return _login()

@bp.route('/Registro')
def registro():
	from .auth import registro as _reg
	return _reg()

# Alias para formulario de registro (plantilla usa url_for('bp.guardar_registro'))
@bp.route('/guardar_registro', methods=['POST'], endpoint='guardar_registro')
def guardar_registro():
	from .auth import guardar_registro as _gr
	return _gr()

# Alias logout esperado en templates como 'bp.logout'
@bp.route('/logout')
def logout():
	from .auth import logout as _lo
	return _lo()

# Aliases admin para compatibilidad con plantillas legacy (url_for('bp.admin_*'))
@bp.route('/admin')
def admin_dashboard():
	from .admin import admin_dashboard as _ad
	return _ad()

@bp.route('/admin/pedidos')
def admin_orders():
	from .admin import admin_orders as _ao
	return _ao()

@bp.route('/admin/pedidos/<int:order_id>')
def admin_order_detail(order_id):
	from .admin import admin_order_detail as _aod
	return _aod(order_id)

@bp.route('/admin/pedidos/<int:order_id>/estado', methods=['POST'])
def admin_update_order_status(order_id):
	from .admin import admin_update_order_status as _au
	return _au(order_id)

@bp.route('/admin/transacciones/vista')
def admin_transacciones_html():
	# Alias para plantilla que llama url_for('bp.admin_transacciones_html')
	from .admin import admin_transacciones_html as _ath
	return _ath()

@bp.route('/admin/producto', methods=['POST'])
def admin_create_product():
	from .admin import admin_create_product as _ac
	return _ac()

@bp.route('/admin/producto/<int:tool_id>', methods=['POST'])
def admin_update_product(tool_id):
	from .admin import admin_update_product as _aup
	return _aup(tool_id)

@bp.route('/admin/usuario/<int:user_id>/rol', methods=['POST'])
def admin_update_user_role(user_id):
	from .admin import admin_update_user_role as _aur
	return _aur(user_id)

# Aliases a rutas de sub-blueprints
@bp.route('/Carrito')
@bp.route('/carrito')
def carrito():
	from .cart import carrito as _c
	return _c()

# Alias para endpoint esperado 'bp.cliente' en templates legacy
@bp.route('/Cliente')
@bp.route('/cliente')
def cliente():
	from .cart import cliente as _cl
	return _cl()

@bp.route('/staff', endpoint='staff_dashboard')
def staff_dashboard_alias():
	from .admin import staff_dashboard as _s
	return _s()

# Aliases carrito (acciones cantidad) usados por templates legacy
@bp.route('/disminuir_cantidad/<int:id_tool>', methods=['POST'])
def disminuir_cantidad(id_tool):
	from .cart import disminuir_cantidad as _dc
	return _dc(id_tool)

@bp.route('/aumentar_cantidad/<int:id_tool>', methods=['POST'])
def aumentar_cantidad(id_tool):
	from .cart import aumentar_cantidad as _ac
	return _ac(id_tool)

@bp.route('/eliminar_item/<int:id_tool>', methods=['POST'])
def eliminar_item(id_tool):
	from .cart import eliminar_item as _ei
	return _ei(id_tool)

# --- Wrappers de compatibilidad: exponen funciones que tests parchean ---
def fetch_tools_filtered(*a, **kw):
	from app.models import fetch_tools_filtered as _f
	return _f(*a, **kw)

def fetch_tool_suggestions(*a, **kw):
	from app.models import fetch_tool_suggestions as _f
	return _f(*a, **kw)

def fetch_all_tools_wrapper():
	from app.models import fetch_all_tools as _f
	return _f()

def fetch_tools_by_code(*a, **kw):
	from app.models import fetch_tools_by_code as _f
	return _f(*a, **kw)

def insert_tools(*a, **kw):
	from app.models import insert_tools as _f
	return _f(*a, **kw)

def delete_tools(*a, **kw):
	from app.models import delete_tools as _f
	return _f(*a, **kw)

def update_tools(*a, **kw):
	from app.models import update_tools as _f
	return _f(*a, **kw)

def _current_user_id(*a, **kw):
	from .cart import _current_user_id as _f
	return _f(*a, **kw)

# Carrito wrappers usados en tests
def get_or_create_order(*a, **kw):
	from app.models import get_or_create_order as _f
	return _f(*a, **kw)

def add_or_update_item(*a, **kw):
	from app.models import add_or_update_item as _f
	return _f(*a, **kw)

def get_cart_totals(*a, **kw):
	from app.models import get_cart_totals as _f
	return _f(*a, **kw)

# Exponer mysql para monkeypatch de tests
from app import mysql  # noqa: E402,F401
