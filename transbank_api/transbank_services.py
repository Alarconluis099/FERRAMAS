from flask import flash, Blueprint, request, jsonify, render_template, redirect, url_for, session, current_app
from app import mysql
import random
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.error.transbank_error import TransbankError
from transbank.webpay.webpay_plus.transaction import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from decimal import Decimal


bp_tbk = Blueprint('tbk', __name__)


@bp_tbk.route("/create", methods=["POST"])
def webpay_plus_create():
    # Obtener datos de la compra
    if 'usuario' not in session:
        # El usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('bp.iniciar_sesion'))

    # Validar amount y que el carrito no esté vacío
    raw_amount = request.form.get("amount")
    if raw_amount is None:
        flash('Monto no proporcionado', 'error')
        return redirect(url_for('bp.carrito'))
    try:
        amount_decimal = Decimal(raw_amount)
    except Exception:
        flash('Monto inválido', 'error')
        return redirect(url_for('bp.carrito'))
    if amount_decimal <= 0:
        flash('El carrito está vacío o el monto es 0. Agrega productos antes de pagar.', 'error')
        return redirect(url_for('bp.carrito'))
    # Verificar que existan filas en pedido
    try:
        cursor_chk = mysql.connection.cursor()
        cursor_chk.execute('SELECT COUNT(*) FROM pedido')
        count = cursor_chk.fetchone()[0]
        cursor_chk.close()
        if count == 0:
            flash('No hay productos en el carrito.', 'error')
            return redirect(url_for('bp.carrito'))
    except Exception:
        flash('No se pudo validar el carrito.', 'error')
        return redirect(url_for('bp.carrito'))

    buy_order = str(random.randrange(1000000, 99999999))
    session_id = str(random.randrange(1000000, 99999999))
    return_url = 'http://localhost:5000/tbk/commit'

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
    # Aplicar descuento (descuento almacenado como porcentaje entero)
    try:
        descuento_pct = Decimal(descuento)
    except Exception:
        descuento_pct = Decimal(0)
    factor = (Decimal(100) - descuento_pct) / Decimal(100)
    total_con_descuento = int((amount_decimal * factor).quantize(Decimal('1')))  # entero
    if total_con_descuento < 0:
        total_con_descuento = 0

    # Crear la transacción con Transbank (evitar llamar si total es 0)
    if total_con_descuento <= 0:
        flash('No se puede crear transacción con monto 0.', 'error')
        return redirect(url_for('bp.carrito'))
    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    try:
        response = tx.create(buy_order, session_id, total_con_descuento, return_url)
    except Exception as e:
        current_app.logger.exception('Error creando transacción Webpay')
        flash('Error iniciando pago. Intenta nuevamente.', 'error')
        return redirect(url_for('bp.carrito'))

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

@bp_tbk.route("/commit", methods=["GET", "POST"])
def webpay_plus_commit():
    token = request.args.get("token_ws")
    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    response = tx.commit(token)

    print("commit for token_ws: {}".format(token))
    print("response: {}".format(response))

    # return render_template('tbk_commit.html', token=token, response=response)

    if response.get('status') == 'AUTHORIZED':
        # Vaciar carrito (tabla pedido) tras compra exitosa
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM pedido")
            mysql.connection.commit()
            cursor.close()
        except Exception as e:
            current_app.logger.exception('No se pudo limpiar el carrito tras el pago')
        flash('Gracias por su compra', 'success')
    else:
        flash('PAGO FALLIDO', 'error')
    return redirect(url_for('bp.inicio'))
    

@bp_tbk.route('/callback', methods=['POST'])
def callback():
    token_ws = request.form.get('token_ws')
    response = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST)).commit(token_ws)

    
    if response.get('status') == 'AUTHORIZED':
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM pedido")
            mysql.connection.commit()
            cursor.close()
        except Exception:
            current_app.logger.exception('No se pudo limpiar el carrito tras el pago (callback)')
        flash('Gracias por su compra', 'success')
    else:
        flash('PAGO FALLIDO', 'error')
    return redirect(url_for('bp.inicio'))





@bp_tbk.route("/refund", methods=["POST"])
def webpay_plus_refund():
    token = request.form.get("token_ws")
    amount = request.form.get("amount")
    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    response = tx.refund(token, amount)
    print("refund for token_ws: {} by amount: {}".format(token, amount))

    try:
        return render_template("tbk_refund.html", token=token, amount=amount, response=response)
    except TransbankError as e:
        current_app.logger.error(f"Refund error: {e}")
        return jsonify({"error": str(e)}), 400
    

    

@bp_tbk.route("/refund-form", methods=["GET"])
def webpay_plus_refund_form():
    return render_template("tbk_refund-form.html")

@bp_tbk.route('/status-form', methods=['GET'])
def show_create():
    return render_template('tbk_status-form.html')

@bp_tbk.route('/status', methods=['POST'])
def status():
    token_ws = request.form.get('token_ws')
    tx = Transaction()
    resp = tx.status(token_ws)
    return render_template('tbk_status.html', response=resp, token=token_ws, req=request.form)