from flask import request, jsonify
from src import src 
from .models import fetch_all_tools, fetch_tools_by_code, insert_tools

@src.route('/tools', methods=['GET'])
def get_tools():
    tools = fetch_all_tools()
    return jsonify(tools)

@src.route('/tools/<code>', methods=['GET'])
def get_tool(code):
    tool = fetch_tools_by_code(code)

    return jsonify(tool)

@src.route('/tool', methods=['POST'])
def create_tools():
    tools_data = request.get_json()
    insert_tools(tools_data)
    return jsonify({'message': 'Herramienta creado exitosamente'}), 201
