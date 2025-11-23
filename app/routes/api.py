from flask import Blueprint, request, jsonify
from flask import current_app
from app import mysql
from app.models import (
    fetch_tools_filtered, fetch_tool_suggestions, fetch_all_tools,
    fetch_tools_by_code, insert_tools, delete_tools, update_tools
)

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/tools')
def api_tools_paginated():
    try:
        page = int(request.args.get('page','1')); per_page = int(request.args.get('per_page','20'))
    except ValueError:
        return jsonify({'ok':False,'error':'Parámetros inválidos'}), 400
    q = request.args.get('q') or None; order = request.args.get('order') or None
    def parse_int_or_none(key):
        v = request.args.get(key);
        if v in (None,''): return None
        try: return int(v)
        except ValueError: return None
    precio_min = parse_int_or_none('precio_min'); precio_max = parse_int_or_none('precio_max')
    # Import diferido para permitir que tests monkeypatch en app.routes.fetch_tools_filtered
    from app import routes as routes_pkg  # type: ignore

    # Intentar usar cache si está disponible para consultas idénticas
    cache = None
    try:
        from app import cache as _c
        cache = _c
    except Exception:
        cache = None

    cache_key = None
    if cache is not None:
        try:
            qs = request.query_string.decode('utf-8') if isinstance(request.query_string, (bytes, bytearray)) else str(request.query_string)
            cache_key = f"api_tools:{qs}:p{page}:pp{per_page}"
            cached = cache.get(cache_key)
            if cached is not None:
                return jsonify(cached)
        except Exception:
            cache_key = None

    items, total = routes_pkg.fetch_tools_filtered(page=page, per_page=per_page, q=q, precio_min=precio_min, precio_max=precio_max, order=order)
    has_more = page * per_page < total
    payload = {'ok':True,'page':page,'per_page':per_page,'total':total,'has_more':has_more,'items':items}
    if cache is not None and cache_key:
        try:
            # Cachear objetos serializables (listas/dicts)
            cache.set(cache_key, payload, timeout=30)
        except Exception:
            pass
    return jsonify(payload)

@api_bp.route('/api/tool_suggestions')
def api_tool_suggestions():
    q = (request.args.get('q') or '').strip()
    if not q: return jsonify({'ok':True,'items':[]})
    return jsonify({'ok':True,'items':fetch_tool_suggestions(q)})

# Herramientas CRUD JSON (respuesta limitada/paginada para evitar payloads enormes)
@api_bp.route('/tools', methods=['GET'])
def get_tools():
    # Compatibilidad legacy: si no hay query params, devolver lista completa (tests esperan esto)
    if not request.args:
        return jsonify(fetch_all_tools())

    try:
        page = int(request.args.get('page', '1'))
        per_page = int(request.args.get('per_page', '100'))
    except Exception:
        page = 1; per_page = 100
    if per_page < 1: per_page = 1
    if per_page > 1000: per_page = 1000
    # Reusar fetch_tools_filtered para devolver una lista limitada y metadata
    items, total = fetch_tools_filtered(page=page, per_page=per_page)
    return jsonify({'ok': True, 'page': page, 'per_page': per_page, 'total': total, 'items': items})

@api_bp.route('/tools/<code>', methods=['GET'])
def get_tool(code): return jsonify(fetch_tools_by_code(code))

@api_bp.route('/tool', methods=['POST'])
def create_tool():
    data = request.get_json(silent=True) or {}; required = {'id_tool','name'}
    if not required.issubset(data): return jsonify({'error':'Faltan campos requeridos'}), 400
    if insert_tools(data): return jsonify({'message':'Herramienta creada exitosamente'}), 201
    return jsonify({'error':'Error al crear herramienta'}), 500

@api_bp.route('/tools/<id>', methods=['DELETE'])
def delete_tool(id):
    try:
        from app import routes as r
        if r.delete_tools(id):
            return jsonify({'message':'Herramienta eliminada correctamente'}), 200
        return jsonify({'message':'Herramienta no encontrada'}), 404
    except Exception as e:
        current_app.logger.exception('Error deleting tool'); return jsonify({'Error':'Error del servidor'}), 500

@api_bp.route('/tools/<id>', methods=['PUT'])
def update_tool(id):
    try:
        data = request.get_json(silent=True) or {}
        from app import routes as r
        if r.update_tools(id, data):
            return jsonify({'message':'Herramienta actualizada correctamente'}), 200
        return jsonify({'message':'Herramienta no encontrada'}), 404
    except Exception:
        current_app.logger.exception('Error updating tool'); return jsonify({'Error':'Error del servidor'}), 500
