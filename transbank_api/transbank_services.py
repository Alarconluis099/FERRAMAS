from flask import flash, Blueprint, request, jsonify, render_template, redirect, url_for, session
from . import mysql
import random

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.error.transbank_error import TransbankError
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.webpay.webpay_plus.transaction import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from decimal import Decimal
from decimal import Decimal


bp = Blueprint('bp', __name__)


@bp.route("/create", methods=["POST"])
def webpay_plus_create():
    # Obtener datos de la compra
    if 'usuario' not in session:
        # El usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('iniciar_sesion'))
    buy_order = str(random.randrange(1000000, 99999999))
    session_id = str(random.randrange(1000000, 99999999))
    amount = int(Decimal(request.form.get("amount")) )  # Convertir a entero y considerar dos decimales
    return_url = 'http://localhost:5000/commit'

    # Obtener el descuento del usuario si está logueado
    descuento = Decimal(0)
    if 'usuario' in session:
        usuario = session['usuario']
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT descuento FROM users WHERE usuario = %s",
            (usuario,)
        )
        result = cursor.fetchone()
        if result:
            descuento = result[0]

    # Aplicar el descuento al monto total y convertir a entero
    total_con_descuento = int(Decimal(amount))

    # Crear la transacción con Transbank
    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    response = tx.create(buy_order, session_id, total_con_descuento, return_url)

    # Después de crear la transacción, actualiza el descuento a 0
    if 'usuario' in session:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE users SET descuento = %s WHERE usuario = %s",
            (0, usuario)
        )
        mysql.connection.commit()

    # Renderizar ruta de destino
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
        return redirect(url_for('inicio'))
    else:
        flash('PAGO FALLIDO', 'error')
        return redirect(url_for('inicio'))
    

@bp.route('/callback', methods=['POST'])
def callback():
    token_ws = request.form.get('token_ws')
    response = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST)).commit(token_ws)

    
    if response['status'] == 'AUTHORIZED':
        flash('PAGO EXITOSO')
        return redirect(url_for('Inicio'))
    else:
        flash('PAGO FALLIDO')
        return redirect(url_for('Inicio'))





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