from flask import request, jsonify
from app import app 
from .models import fetch_all_tools, fetch_tools_by_code, insert_tools
from flask_mysqldb import MySQL

conexion = MySQL(app)

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
    return jsonify({'message': 'Herramienta creado exitosamente'}), 201

@app.route('/herramientas')
def listar_herramientas():
    return "Aquí van herramientas"


def error_page(error):
    return "PÁGINA NO ENCONTRADA..."
app.register_error_handler(404, error_page)


