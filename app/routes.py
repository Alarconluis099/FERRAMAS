from flask import Blueprint, request, flash, get_flashed_messages, jsonify, render_template, redirect, url_for, session
from app import app
from .models import fetch_all_tools, fetch_tools_by_code, insert_tools, delete_tools, update_tools, get_all_users, fetch_users_by_id, fetch_all_pedidos_ready
from . import mysql
import random


@app.route('/Carrito')
def carrito():
    pedidos = fetch_all_pedidos_ready()
    return render_template('carrito.html', pedidos=pedidos,)

@app.route('/Pedidos')
def ver_pedidos():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM pedido")  # Obtener todos los pedidos
    pedido = cursor.fetchall()
    cursor.close()

    # Convertir los resultados a una lista de diccionarios
    pedidos_dict = []
    for pedidos in pedido:
        columns = [column[0] for column in cursor.description]
        pedidos_dict.append(dict(zip(columns, pedidos)))

    return render_template('pedidos.html', pedido=pedidos_dict)


@app.route('/disminuir_cantidad/<int:product_id>', methods=['POST'])
def disminuir_cantidad(product_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT cantidad FROM pedido WHERE id_pedido = %s", (product_id,))
    result = cursor.fetchone()

    if result:
        cantidad = result[0]
        if cantidad > 1:
            nueva_cantidad = cantidad - 1
            cursor.execute(
                "UPDATE pedido SET cantidad = %s WHERE id_pedido = %s",
                (nueva_cantidad, product_id)
            )
        else:
            cursor.execute("DELETE FROM pedido WHERE id_pedido = %s", (product_id,))

        mysql.connection.commit()

    cursor.close()
    return redirect(url_for('carrito'))


@app.route('/aumentar_cantidad/<int:product_id>', methods=['POST'])
def aumentar_cantidad(product_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT cantidad FROM pedido WHERE id_pedido = %s", (product_id,))
    result = cursor.fetchone()

    if result:
        cantidad = result[0]
        if cantidad > 1:
            nueva_cantidad = cantidad + 1
            cursor.execute(
                "UPDATE pedido SET cantidad = %s WHERE id_pedido = %s",
                (nueva_cantidad, product_id)
            )
        else:
            cursor.execute("DELETE FROM pedido WHERE id_pedido = %s", (product_id,))

        mysql.connection.commit()

    cursor.close()
    return redirect(url_for('carrito'))


@app.route('/guardar_pedido', methods=['POST'])
def guardar_pedido():
    product_id = request.form['product_id']
    product_name = request.form['product_name']
    product_description = request.form['product_description']
    product_price = request.form['product_price']
    product_quantity = int(request.form['cantidad'])

    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT * FROM pedido WHERE id_pedido = %s", (product_id,)
    )
    existing_order = cursor.fetchone()

    if existing_order:
        new_quantity = existing_order[4] + product_quantity
        cursor.execute(
            "UPDATE pedido SET cantidad = %s WHERE id_pedido = %s",
            (new_quantity, product_id)
        )
    else:
        cursor.execute(
            "INSERT INTO pedido (id_pedido, nom_pedido, desc_pedido, precio_pedido, cantidad) VALUES (%s, %s, %s, %s, %s)",
            (product_id, product_name, product_description, product_price, product_quantity)
        )
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('inicio'))



@app.route('/Pedido', methods=['GET'])
def pedido():
    pedido = fetch_all_pedidos_ready()
    return jsonify(pedido)

@app.route('/users', methods=['GET'])
def get_users():
    users = get_all_users()
    return jsonify(users)

@app.route('/users', methods=['GET'])
def get_users_by_id():
    users = fetch_users_by_id()
    return jsonify(users)

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
    
@app.route('/')
def main():
    return redirect('Inicio')

@app.route('/Cliente')
def cliente():
    return render_template('Cliente.html')



@app.route('/Inicio')
def inicio():
    session.pop('pedidos', None)
    tools = fetch_all_tools()
    return render_template('inicio.html', tools=tools)

@app.route('/Login')
def login():
    return render_template('login.html')

@app.route('/Registro')
def registro():
    return render_template('registro.html')

@app.route('/Equipos_medicion')
def equipos_medicion():
    return render_template('equipos-medicion.html')

@app.route('/Equipos_seguridad')
def equipos_seguridad():
    return render_template('equipos-seguridad.html')

@app.route('/Fijaciones_adhesivos')
def fijaciones_adhesivos():
    return render_template('fijaciones-adhesivos.html')

@app.route('/Herramientas_manuales')
def herramientas_manuales():
    return render_template('herramientas-manuales.html')

@app.route('/Materiales_basicos')
def materiales_basicos():
    return render_template('materiales-basicos.html')

@app.route('/Tornillos_anclajes')
def tornillos_anclajes():
    return render_template('tornillos-anclajes.html')

# Herramientas manuales - Subcategorias

@app.route('/martillos')
def martillos():
    return render_template('HM-martillos.html')

@app.route('/destornillador')
def destornillador():
    return render_template('HM-destornillador.html')

@app.route('/llaves')
def llaves():
    return render_template('HM-llaves.html')

@app.route('/electricas')
def electricas():
    return render_template('HM-electricas.html')

app.route('/taladros')
def taladros():
    return render_template('HM-taladros.html')

app.route('/sierras')
def sierras():
    return render_template('HM-sierras.html')

app.route('/lijadoras')
def lijadoras():
    return render_template('HM-lijadoras.html')

app.route('/materiales')
def materiales():
    return render_template('HM-materiales.html')

    
# Rutas Transbank

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.error.transbank_error import TransbankError
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.webpay.webpay_plus.transaction import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

bp = Blueprint('routes', __name__)

@bp.route("/create", methods=["POST"])
def webpay_plus_create():
    # print("Webpay Plus Transaction.create")
    buy_order = str(random.randrange(1000000, 99999999))
    session_id = str(random.randrange(1000000, 99999999))
    amount = request.form.get("amount")
    return_url = 'http://localhost:5000/commit'


    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    response = tx.create(buy_order, session_id, amount, return_url)

    return redirect(response['url'] + '?token_ws=' + response['token'])



@bp.route("/commit", methods=["GET", "POST"])
def webpay_plus_commit():
    token = request.args.get("token_ws")
    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    response = tx.commit(token)

    print("commit for token_ws: {}".format(token))
    print("response: {}".format(response))

    # return render_template('tbk_commit.html', token=token, response=response)

    if response['status'] == 'AUTHORIZED':
        flash('PAGO EXITOSO', 'success')
        return redirect(url_for('inicio', status='PAGO EXITOSO'))
    else:
        flash('PAGO FALLIDO', 'error')
        return redirect(url_for('inicio', status='PAGO FALLIDO'))
    

@bp.route('/callback', methods=['POST'])
def callback():
    token_ws = request.form.get('token_ws')
    response = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST)).commit(token_ws)

    
    if response['status'] == 'AUTHORIZED':
        flash('PAGO EXITOSO')
        return redirect(url_for('Inicio', status='PAGO EXITOSO'))
    else:
        flash('PAGO FALLIDO')
        return redirect(url_for('Inicio', status='PAGO FALLIDO'))





@bp.route("/refund", methods=["POST"])
def webpay_plus_refund():
    token = request.form.get("token_ws")
    amount = request.form.get("amount")
    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    response = tx.refund(token, amount)
    print("refund for token_ws: {} by amount: {}".format(token, amount))

    try:
        response = Transaction.refund(token, amount)
        print("response: {}".format(response))

        return render_template("tbk_refund.html", token=token, amount=amount, response=response)
    except TransbankError as e:
        print(e.message)
        return jsonify({"error": e.message}), 400
    

    

@bp.route("/refund-form", methods=["GET"])
def webpay_plus_refund_form():
    return render_template("tbk_refund-form.html")

@bp.route('/status-form', methods=['GET'])
def show_create():
    return render_template('tbk_status-form.html')

@bp.route('/status', methods=['POST'])
def status():
    token_ws = request.form.get('token_ws')
    tx = Transaction()
    resp = tx.status(token_ws)
    return render_template('tbk_status.html', response=resp, token=token_ws, req=request.form)


def error_page(error):
    return "PÁGINA NO ENCONTRADA..."
app.register_error_handler(404, error_page)


