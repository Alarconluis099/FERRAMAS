from flask import request, jsonify
from app import app 
from .models import fetch_all_tools, fetch_tools_by_code, insert_tools

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

@app.route('/hola')
def index():
    return "hola soy un texto"