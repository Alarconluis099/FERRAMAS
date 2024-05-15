from flask import request, jsonify
from app import app 
from .models import fetch_all_tools, fetch_tools_by_code, insert_tools, delete_tools, update_tools
# from flask_mysqldb import MySQL

# conexion = MySQL(app)

@app.route('/tools', methods=['GET'])
def get_tools():
    tools = fetch_all_tools()
    return jsonify(tools)


@app.route('/tools/<code>', methods=['GET'])
def get_tool(code):
    tool = fetch_tools_by_code(code)

    return jsonify(tool)


@app.route('/tool', methods=['POST'])
def create_tools():
    tools_data = request.get_json()
    insert_tools(tools_data)
    return jsonify({'message': 'Herramienta creada exitosamente'}), 200


@app.route('/tools/<id>', methods=['DELETE'])
def delete_tool_route(id):
    try:
        eliminada = delete_tools(id)

        if eliminada:
            return jsonify({'message': 'Herramienta eliminada correctamente'}), 200
        else:
            return jsonify({'message': 'Herramienta no encontrada'}), 404
    except Exception:
        return jsonify({'Error': 'Error del servidor'}), 500
    

@app.route('/tools/<id>', methods=['PUT'])
def update_tool_route(id):
    try:
        tools_data = request.json
        update = update_tools(id, tools_data)

        if update:
            return jsonify({'message': 'Herramienta actualizada correctamente'}), 200
        else:
            return jsonify({'message': 'Herramienta no encontrada'}), 404
    except Exception:
        return jsonify({'Error': 'Error del servidor'}), 500


def error_page(error):
    return "PÁGINA NO ENCONTRADA..."
app.register_error_handler(404, error_page)


