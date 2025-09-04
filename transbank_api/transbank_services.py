from flask import flash, Blueprint, request, jsonify, render_template, redirect, url_for, session, current_app
from app import mysql
from app.models import get_user_open_order, get_cart_items, get_cart_totals, clear_order_items, finalize_order, insert_transaction
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
    """Crea la transacción Webpay validando el carrito según el esquema normalizado.
    Recalcula el monto (ignora el hidden enviado) y revalida stock antes de llamar a Transbank."""
    if 'usuario' not in session:
        return redirect(url_for('bp.iniciar_sesion'))

    usuario = session['usuario']
    # Obtener id usuario y descuento_porcentaje
    try:
        cur_user = mysql.connection.cursor()
        cur_user.execute("SELECT id_user, COALESCE(descuento_porcentaje,0) FROM users WHERE usuario=%s", (usuario,))
        row_user = cur_user.fetchone()
        cur_user.close()
        if not row_user:
            flash('Usuario no encontrado.', 'error')
            return redirect(url_for('bp.carrito'))
        user_id, descuento_pct = row_user[0], int(row_user[1] or 0)
    except Exception:
        flash('No se pudo validar el usuario.', 'error')
        return redirect(url_for('bp.carrito'))

    # Pedido abierto
    order_id = get_user_open_order(user_id)
    if not order_id:
        flash('No hay productos en el carrito.', 'error')
        return redirect(url_for('bp.carrito'))
    items = get_cart_items(order_id)
    if not items:
        flash('No hay productos en el carrito.', 'error')
        return redirect(url_for('bp.carrito'))

    # Revalidar stock actual
    try:
        ids = [it['id_tool'] for it in items]
        placeholders = ','.join(['%s'] * len(ids))
        cur_stock = mysql.connection.cursor()
        cur_stock.execute(f"SELECT id_tool, stock FROM tools WHERE id_tool IN ({placeholders})", tuple(ids))
        stock_rows = cur_stock.fetchall()
        cur_stock.close()
        stock_map = {r[0]: r[1] for r in stock_rows}
        insuficiente = [it for it in items if it['id_tool'] not in stock_map or it['cantidad'] > stock_map[it['id_tool']]]
        if insuficiente:
            nombres = ', '.join([it['name'] for it in insuficiente])
            flash(f'Stock insuficiente para: {nombres}. Actualiza tu carrito.', 'error')
            return redirect(url_for('bp.carrito'))
    except Exception:
        flash('No se pudo validar el stock.', 'error')
        return redirect(url_for('bp.carrito'))

    # Recalcular subtotal desde la BD
    subtotal = 0
    for it in items:
        try:
            subtotal += int(it['cantidad']) * int(it['precio_unitario'])
        except Exception:
            pass
    if subtotal <= 0:
        flash('El carrito está vacío.', 'error')
        return redirect(url_for('bp.carrito'))

    # Aplicar descuento porcentaje
    factor = (Decimal(100) - Decimal(descuento_pct)) / Decimal(100)
    total_con_descuento = int((Decimal(subtotal) * factor).quantize(Decimal('1')))
    if total_con_descuento <= 0:
        flash('Monto inválido para la transacción.', 'error')
        return redirect(url_for('bp.carrito'))

    buy_order = str(random.randrange(1000000, 99999999))
    session_id = str(random.randrange(1000000, 99999999))
    return_url = 'http://localhost:5000/tbk/commit'

    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    try:
        response = tx.create(buy_order, session_id, total_con_descuento, return_url)
    except Exception:
        current_app.logger.exception('Error creando transacción Webpay')
        flash('Error iniciando pago. Intenta nuevamente.', 'error')
        return redirect(url_for('bp.carrito'))

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
        # Identificar pedido abierto del usuario y procesar
        try:
            user = session.get('usuario')
            order_id = None
            if user:
                cur = mysql.connection.cursor()
                cur.execute("SELECT id_user, COALESCE(descuento_porcentaje,0) FROM users WHERE usuario=%s", (user,))
                row = cur.fetchone()
                descuento_pct = 0
                if row:
                    from app.models import get_user_open_order
                    order_id = get_user_open_order(row[0])
                    descuento_pct = int(row[1] or 0)
                cur.close()
            if order_id:
                items = get_cart_items(order_id)
                total, _ = get_cart_totals(order_id)
                # Descontar stock por item
                cur2 = mysql.connection.cursor()
                for it in items:
                    cur2.execute("UPDATE tools SET stock = GREATEST(stock - %s,0) WHERE id_tool=%s", (it['cantidad'], it['id_tool']))
                mysql.connection.commit()
                cur2.close()
                finalize_order(order_id, total)
                insert_transaction(order_id, total)
                clear_order_items(order_id)
                # Consumir descuento solo tras compra exitosa
                if descuento_pct > 0:
                    cur3 = mysql.connection.cursor()
                    cur3.execute("UPDATE users SET descuento_porcentaje=0 WHERE usuario=%s", (user,))
                    mysql.connection.commit()
                    cur3.close()
        except Exception:
            current_app.logger.exception('Fallo procesando pedido tras pago')
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
            user = session.get('usuario')
            order_id = None
            if user:
                cur = mysql.connection.cursor()
                cur.execute("SELECT id_user, COALESCE(descuento_porcentaje,0) FROM users WHERE usuario=%s", (user,))
                row = cur.fetchone()
                descuento_pct = 0
                if row:
                    order_id = get_user_open_order(row[0])
                    descuento_pct = int(row[1] or 0)
                cur.close()
            if order_id:
                items = get_cart_items(order_id)
                total, _ = get_cart_totals(order_id)
                cur2 = mysql.connection.cursor()
                for it in items:
                    cur2.execute("UPDATE tools SET stock = GREATEST(stock - %s,0) WHERE id_tool=%s", (it['cantidad'], it['id_tool']))
                mysql.connection.commit()
                cur2.close()
                finalize_order(order_id, total)
                insert_transaction(order_id, total)
                clear_order_items(order_id)
                if descuento_pct > 0:
                    cur3 = mysql.connection.cursor()
                    cur3.execute("UPDATE users SET descuento_porcentaje=0 WHERE usuario=%s", (user,))
                    mysql.connection.commit()
                    cur3.close()
        except Exception:
            current_app.logger.exception('Fallo procesando pedido tras pago (callback)')
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