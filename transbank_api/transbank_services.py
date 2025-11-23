from flask import flash, Blueprint, request, jsonify, render_template, redirect, url_for, session, current_app
from app import mysql
from app.models import get_user_open_order, get_cart_items, get_cart_totals, finalize_order, insert_transaction
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
    # Refuerzo: restaurar sesión si se perdió antes de crear transacción
    if not session.get('usuario') and order_id:
        try:
            curu = mysql.connection.cursor()
            curu.execute("SELECT id_user FROM pedidos WHERE id_pedido=%s", (order_id,))
            rp = curu.fetchone()
            if rp and rp[0]:
                uid = rp[0]
                curu.execute("SELECT usuario, COALESCE(role,'') FROM users WHERE id_user=%s", (uid,))
                ruser = curu.fetchone()
                if ruser:
                    session['id_user'] = int(uid)
                    session['usuario'] = ruser[0]
                    session['rol'] = (ruser[1] or ('admin' if ruser[0] == 'admin' else None))
        except Exception as e:
            current_app.logger.error('[TBK CREATE][REFUERZO] No se pudo restaurar usuario desde pedido %s: %s', order_id, e)
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
    return_url = current_app.config.get('RETURN_URL_TBK', 'http://localhost:5000/tbk/commit')

    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    try:
        response = tx.create(buy_order, session_id, total_con_descuento, return_url)
        token = response['token']
        # Guardar fila "pending" para poder recuperar pedido aunque se pierda la cookie de sesión
        try:
            curp = mysql.connection.cursor()
            curp.execute("INSERT INTO transacciones (id_pedido, monto_transaccion, metodo_pago, token, status) VALUES (%s,%s,%s,%s,%s)", (order_id, total_con_descuento, 'Webpay Plus', token, 'pending'))
            mysql.connection.commit(); curp.close()
        except Exception:
            mysql.connection.rollback()
            current_app.logger.warning('[TBK CREATE] No se pudo registrar transacción pending (token=%s)', token)
        return redirect(response['url'] + '?token_ws=' + token)
    except Exception:
        current_app.logger.exception('Error creando transacción Webpay')
        flash('Error iniciando pago. Intenta nuevamente.', 'error')
        return redirect(url_for('bp.carrito'))

@bp_tbk.route("/commit", methods=["GET", "POST"])
def webpay_plus_commit():
    token = request.args.get("token_ws") or request.form.get('token_ws')
    if not token:
        flash('Token de pago no recibido.', 'error')
        return redirect(url_for('bp.inicio'))
    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    response = tx.commit(token)

    print("commit for token_ws: {}".format(token))
    print("response: {}".format(response))

    # return render_template('tbk_commit.html', token=token, response=response)

    # Refuerzo: actualizar monto_total del pedido con el amount recibido en la respuesta de Transbank
    amount_from_tbk = response.get('amount')
    order_id_from_token = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id_pedido FROM transacciones WHERE token=%s", (token,))
        row = cur.fetchone()
        current_app.logger.info('[TBK COMMIT][LOG] amount_from_tbk=%s, token=%s, row=%s', amount_from_tbk, token, row)
        if row:
            order_id_from_token = row[0]
            if amount_from_tbk and order_id_from_token:
                cur.execute("UPDATE pedidos SET monto_total=%s WHERE id_pedido=%s", (amount_from_tbk, order_id_from_token))
                mysql.connection.commit()
                current_app.logger.info('[TBK COMMIT][LOG] UPDATE pedidos SET monto_total=%s WHERE id_pedido=%s (rowcount=%s)', amount_from_tbk, order_id_from_token, cur.rowcount)
            else:
                current_app.logger.warning('[TBK COMMIT][LOG] No se actualizó monto_total porque amount_from_tbk o order_id_from_token es None. amount_from_tbk=%s, order_id_from_token=%s', amount_from_tbk, order_id_from_token)
        else:
            current_app.logger.warning('[TBK COMMIT][LOG] No se encontró order_id para token=%s', token)
        cur.close()
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.error('[TBK COMMIT][REFUERZO] Error actualizando monto_total desde respuesta Transbank: %s', e)

    status_resp = response.get('status')
    if status_resp == 'AUTHORIZED':
        current_app.logger.info('[TBK COMMIT] AUTORIZADO token=%s', token)
        # Identificar pedido abierto del usuario y procesar
        try:
            user = session.get('usuario')
            order_id = None
            descuento_pct = 0
            current_app.logger.info(f'[TBK COMMIT][DEBUG] token={token}')
            if user:
                current_app.logger.info('[TBK COMMIT] Usuario en sesión: %s', user)
                cur = mysql.connection.cursor()
                cur.execute("SELECT id_user, COALESCE(descuento_porcentaje,0) FROM users WHERE usuario=%s", (user,))
                row = cur.fetchone()
                cur.close()
                if row:
                    from app.models import get_user_open_order
                    order_id = get_user_open_order(row[0])
                    descuento_pct = int(row[1] or 0)
                    current_app.logger.info('[TBK COMMIT] order_id=%s descuento_pct=%s', order_id, descuento_pct)
            # Refuerzo: si no hay usuario en sesión, pero tenemos order_id, restaurar usuario desde el pedido
            if not user and order_id:
                try:
                    curu = mysql.connection.cursor()
                    curu.execute("SELECT id_user FROM pedidos WHERE id_pedido=%s", (order_id,))
                    rp = curu.fetchone()
                    if rp and rp[0]:
                        uid = rp[0]
                        curu.execute("SELECT usuario, COALESCE(role,'') FROM users WHERE id_user=%s", (uid,))
                        ruser = curu.fetchone()
                        if ruser:
                            session['id_user'] = int(uid)
                            session['usuario'] = ruser[0]
                            session['rol'] = (ruser[1] or ('admin' if ruser[0] == 'admin' else None))
                            current_app.logger.info('[TBK COMMIT][REFUERZO] Sesión restaurada para usuario=%s id_user=%s', ruser[0], uid)
                    curu.close()
                except Exception as e:
                    current_app.logger.error('[TBK COMMIT][REFUERZO] No se pudo restaurar usuario desde pedido %s: %s', order_id, e)

            # Fallback: si no hay sesión (cookie SameSite bloqueada en POST) buscamos por token
            if not order_id:
                curtok = mysql.connection.cursor()
                curtok.execute("SELECT id_pedido FROM transacciones WHERE token=%s", (token,))
                rowt = curtok.fetchone()
                curtok.close()
                if rowt:
                    order_id = rowt[0]
                    current_app.logger.info('[TBK COMMIT] Recuperado order_id=%s desde token', order_id)
                    # Intentar restaurar sesión del usuario relacionada al pedido para que no se cierre sesión al volver
                    try:
                        curp2 = mysql.connection.cursor()
                        curp2.execute("SELECT id_user FROM pedidos WHERE id_pedido=%s", (order_id,))
                        rp = curp2.fetchone()
                        curp2.close()
                        if rp and rp[0]:
                            uid = rp[0]
                            curu = mysql.connection.cursor()
                            curu.execute("SELECT usuario, COALESCE(role,'') FROM users WHERE id_user=%s", (uid,))
                            ruser = curu.fetchone()
                            curu.close()
                            if ruser:
                                try:
                                    session['id_user'] = int(uid)
                                except Exception:
                                    pass
                                try:
                                    session['usuario'] = ruser[0]
                                except Exception:
                                    pass
                                try:
                                    session['rol'] = (ruser[1] or ('admin' if ruser[0] == 'admin' else None))
                                except Exception:
                                    pass
                                current_app.logger.info('[TBK COMMIT] Sesión restaurada para usuario=%s id_user=%s', ruser[0], uid)
                        else:
                            # Refuerzo: si no hay usuario, igual forzar update de pedido para flujos tipo JMeter
                            current_app.logger.warning('[TBK COMMIT][JMeter] No se pudo restaurar usuario, pero se forzará update de pedido id=%s', order_id)
                    except Exception:
                        current_app.logger.exception('[TBK COMMIT] No se pudo restaurar sesión desde pedido %s', order_id)
                else:
                    current_app.logger.warning('[TBK COMMIT] No se encontró transacción pending para token=%s', token)

            # LOG status recibido y robustecer comparación
            status = response.get('status', '').strip().upper()
            current_app.logger.info(f'[TBK COMMIT][DEBUG] status recibido: "{status}" para token={token}')

            if status != 'AUTHORIZED':
                current_app.logger.warning(f"[TBK COMMIT] Estado no autorizado token={token} status={status}")
                # Log extra de contexto
                current_app.logger.warning(f"[TBK COMMIT][DEBUG] order_id={order_id} user={user}")
                return render_template('error_pago.html', mensaje="Pago no autorizado")

            current_app.logger.info(f'[TBK COMMIT] Pago autorizado, procesando pedido {order_id}')

            if order_id:
                # Import seguro para evitar UnboundLocalError
                from app.models import get_cart_items
                items = get_cart_items(order_id)
                total, _ = get_cart_totals(order_id)
                current_app.logger.info('[TBK COMMIT] items=%s total=%s', len(items), total)
                current_app.logger.info('[TBK COMMIT][DEBUG] items detalle: %s', items)
                # Loguear el contenido real de pedido_detalle
                try:
                    cur_det = mysql.connection.cursor()
                    cur_det.execute("SELECT id_detalle, id_tool, cantidad, precio_unitario FROM pedido_detalle WHERE id_pedido=%s", (order_id,))
                    rows_det = cur_det.fetchall()
                    current_app.logger.info('[TBK COMMIT][DEBUG] pedido_detalle para id_pedido=%s: %s', order_id, rows_det)
                    cur_det.close()
                except Exception as e:
                    current_app.logger.error('[TBK COMMIT][DEBUG] Error consultando pedido_detalle: %s', e)
                # Refuerzo: si el total es 0, intentar obtenerlo desde transacciones AUTHORIZED
                if total == 0:
                    try:
                        cur_monto = mysql.connection.cursor()
                        cur_monto.execute("SELECT monto_transaccion FROM transacciones WHERE id_pedido=%s AND status='AUTHORIZED' ORDER BY id_transaccion DESC LIMIT 1", (order_id,))
                        row_monto = cur_monto.fetchone()
                        if row_monto and row_monto[0] and row_monto[0] > 0:
                            total = int(row_monto[0])
                            current_app.logger.info('[TBK COMMIT][REFUERZO] total recuperado desde transacciones: %s', total)
                        cur_monto.close()
                    except Exception as e:
                        current_app.logger.error('[TBK COMMIT][REFUERZO] Error recuperando monto desde transacciones: %s', e)
                # Descontar stock por item
                cur2 = mysql.connection.cursor()
                for it in items:
                    # Log stock antes
                    try:
                        cur2.execute("SELECT stock FROM tools WHERE id_tool=%s", (it['id_tool'],))
                        stock_before = cur2.fetchone()
                        stock_before = stock_before[0] if stock_before else None
                    except Exception as e:
                        stock_before = None
                        current_app.logger.error('[TBK COMMIT][DEBUG] Error leyendo stock antes: %s', e)
                    cur2.execute("UPDATE tools SET stock = GREATEST(stock - %s,0) WHERE id_tool=%s", (it['cantidad'], it['id_tool']))
                    affected = cur2.rowcount
                    # Log stock después
                    try:
                        cur2.execute("SELECT stock FROM tools WHERE id_tool=%s", (it['id_tool'],))
                        stock_after = cur2.fetchone()
                        stock_after = stock_after[0] if stock_after else None
                    except Exception as e:
                        stock_after = None
                        current_app.logger.error('[TBK COMMIT][DEBUG] Error leyendo stock después: %s', e)
                    current_app.logger.debug('[TBK COMMIT] Stock update for id_tool=%s affected=%s antes=%s después=%s', it['id_tool'], affected, stock_before, stock_after)
                mysql.connection.commit()
                cur2.close()
                # Finalizar pedido (marca estado 'completado' y guarda monto)
                try:
                    finalize_order(order_id, total)
                except Exception:
                    current_app.logger.exception('[TBK COMMIT] finalize_order failed for order_id=%s', order_id)
                # Asegurar en la BD que el pedido quede en estado 'completado' y monto correcto
                try:
                    curup = mysql.connection.cursor()
                    # Si el monto recibido de Transbank es mayor a cero, forzar el update
                    if total > 0:
                        try:
                            curup.execute("UPDATE pedidos SET estado_pedido='completado', monto_total=%s WHERE id_pedido=%s", (total, order_id))
                            mysql.connection.commit()
                            current_app.logger.info('[TBK COMMIT] pedidos updated rows=%s for id=%s (monto_total=%s)', curup.rowcount, order_id, total)
                            if curup.rowcount == 0:
                                current_app.logger.warning('[TBK COMMIT][WARN] El UPDATE de monto_total no afectó filas. order_id=%s monto_total=%s', order_id, total)
                        except Exception as e:
                            mysql.connection.rollback()
                            current_app.logger.error('[TBK COMMIT][ERROR] Error actualizando monto_total=%s para pedido %s: %s', total, order_id, e)
                            if abs(total) > 32767:
                                current_app.logger.error('[TBK COMMIT][ERROR] El monto_total excede el rango de SMALLINT. Considera cambiar el tipo de dato a INT o BIGINT en la base de datos.')
                    else:
                        # Si el monto es cero, intentar obtenerlo desde transacciones
                        curup.execute("SELECT monto_transaccion FROM transacciones WHERE id_pedido=%s AND status='AUTHORIZED' ORDER BY id_transaccion DESC LIMIT 1", (order_id,))
                        row = curup.fetchone()
                        if row and row[0] and row[0] > 0:
                            curup.execute("UPDATE pedidos SET estado_pedido='completado', monto_total=%s WHERE id_pedido=%s", (row[0], order_id))
                            mysql.connection.commit()
                            current_app.logger.info('[TBK COMMIT] pedidos updated rows=%s for id=%s (monto_total recuperado=%s)', curup.rowcount, order_id, row[0])
                    curup.close()
                except Exception:
                    mysql.connection.rollback(); current_app.logger.exception('[TBK COMMIT] Could not ensure pedidos.estado_pedido=completado for order_id=%s', order_id)
                # Actualizar transacción pending -> AUTHORIZED (si existe); si no, insertar
                try:
                    curtx = mysql.connection.cursor()
                    curtx.execute("UPDATE transacciones SET status='AUTHORIZED', monto_transaccion=%s WHERE token=%s", (total, token))
                    updated = curtx.rowcount
                    if updated == 0:
                        curtx.execute("INSERT INTO transacciones (id_pedido, monto_transaccion, metodo_pago, token, status) VALUES (%s,%s,%s,%s,%s)", (order_id, total, 'Webpay Plus', token, 'AUTHORIZED'))
                        current_app.logger.info('[TBK COMMIT] transacciones inserted for token=%s order=%s', token, order_id)
                    else:
                        current_app.logger.info('[TBK COMMIT] transacciones updated rows=%s for token=%s', updated, token)
                    mysql.connection.commit(); curtx.close()
                except Exception:
                    mysql.connection.rollback(); current_app.logger.exception('[TBK COMMIT] Error actualizando transacción token=%s', token)
                    # Intento de emergencia: insertar registro mínimo sin token (evita perder evidencia)
                    try:
                        curtx2 = mysql.connection.cursor()
                        curtx2.execute("INSERT INTO transacciones (id_pedido, monto_transaccion, metodo_pago, status) VALUES (%s,%s,%s,%s)", (order_id, total, 'Webpay Plus', 'AUTHORIZED'))
                        mysql.connection.commit(); curtx2.close()
                    except Exception:
                        mysql.connection.rollback(); current_app.logger.exception('[TBK COMMIT] Fallback insert también falló order_id=%s', order_id)
                # No borramos items para preservar historial.
                # Consumir descuento solo tras compra exitosa
                if descuento_pct > 0:
                    cur3 = mysql.connection.cursor()
                    cur3.execute("UPDATE users SET descuento_porcentaje=0 WHERE usuario=%s", (user,))
                    mysql.connection.commit()
                    cur3.close()
            else:
                current_app.logger.warning('[TBK COMMIT] No se encontró pedido abierto para usuario=%s', user)
        except Exception:
            current_app.logger.exception('Fallo procesando pedido tras pago')
        flash('Gracias por su compra', 'success')
    # Aseguramiento final: si existe transacción con token y pedido relacionado, marcar pedido como completado
    try:
        try:
            curchk = mysql.connection.cursor()
            curchk.execute("SELECT id_pedido, status, monto_transaccion FROM transacciones WHERE token=%s", (token,))
            trow = curchk.fetchone(); curchk.close()
            if trow and trow[0]:
                pid = trow[0]
                try:
                    curpre = mysql.connection.cursor()
                    curpre.execute("SELECT estado_pedido, monto_total FROM pedidos WHERE id_pedido=%s", (pid,))
                    prow = curpre.fetchone(); curpre.close()
                    current_app.logger.info('[TBK COMMIT] Post-check pedido id=%s estado_pre=%s', pid, prow[0] if prow else None)
                except Exception:
                    pass
                try:
                    # Use monto from transacciones if provided, else leave total
                    monto_to_set = trow[2] if (trow[2] not in (None, 0)) else None
                    if monto_to_set is not None:
                        curup = mysql.connection.cursor(); curup.execute("UPDATE pedidos SET estado_pedido='completado', monto_total=%s WHERE id_pedido=%s", (monto_to_set, pid)); mysql.connection.commit(); curup.close()
                    else:
                        curup = mysql.connection.cursor(); curup.execute("UPDATE pedidos SET estado_pedido='completado' WHERE id_pedido=%s", (pid,)); mysql.connection.commit(); curup.close()
                    current_app.logger.info('[TBK COMMIT] Asegurado pedido id=%s estado=completado (via transacciones)', pid)
                except Exception:
                    mysql.connection.rollback(); current_app.logger.exception('[TBK COMMIT] No se pudo asegurar pedido %s desde transacciones', pid)
                    # Refuerzo: si el pedido sigue pendiente y monto_total=0, recalcular desde pedido_detalle
                    try:
                        curfix = mysql.connection.cursor()
                        curfix.execute("SELECT estado_pedido, monto_total FROM pedidos WHERE id_pedido=%s", (pid,))
                        prow2 = curfix.fetchone()
                        if prow2 and prow2[0] == 'pendiente' and (prow2[1] is None or prow2[1] == 0):
                            from app.models import get_cart_items, finalize_order
                            items = get_cart_items(pid)
                            monto = sum([it['cantidad'] * it['precio_unitario'] for it in items])
                            if monto > 0:
                                finalize_order(pid, monto)
                                curfix.execute("UPDATE pedidos SET monto_total=%s, estado_pedido='completado' WHERE id_pedido=%s", (monto, pid))
                                mysql.connection.commit()
                                current_app.logger.info('[TBK COMMIT][FORCE-FIX] Pedido %s actualizado a completado con monto %s', pid, monto)
                        curfix.close()
                    except Exception as e:
                        mysql.connection.rollback()
                        current_app.logger.error('[TBK COMMIT][FORCE-FIX] Error al actualizar pedido %s: %s', pid, e)
        except Exception:
            pass
    except Exception:
        current_app.logger.exception('[TBK COMMIT] Error en post-check de transacciones para token=%s', token)

    # Sólo marcar como fallida si el estado retornado NO fue AUTHORIZED
    if status_resp != 'AUTHORIZED':
        current_app.logger.warning('[TBK COMMIT] Estado no autorizado token=%s status=%s', token, status_resp)
        # Actualizar transacción a failed si existe
        try:
            curf = mysql.connection.cursor()
            curf.execute("UPDATE transacciones SET status=%s WHERE token=%s", (status_resp or 'FAILED', token))
            mysql.connection.commit(); curf.close()
        except Exception:
            mysql.connection.rollback(); current_app.logger.exception('[TBK COMMIT] No se pudo marcar transacción fallida token=%s', token)
        flash('PAGO FALLIDO', 'error')

    return redirect(url_for('bp.inicio'))
    

@bp_tbk.route('/callback', methods=['POST'])
def callback():
    token_ws = request.form.get('token_ws')
    response = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST)).commit(token_ws)

    
    if response.get('status') == 'AUTHORIZED':
        current_app.logger.info('[TBK CALLBACK] AUTORIZADO token=%s', token_ws)
        try:
            user = session.get('usuario')
            order_id = None
            if user:
                current_app.logger.info('[TBK CALLBACK] Usuario en sesión: %s', user)
                cur = mysql.connection.cursor()
                cur.execute("SELECT id_user, COALESCE(descuento_porcentaje,0) FROM users WHERE usuario=%s", (user,))
                row = cur.fetchone()
                descuento_pct = 0
                if row:
                    order_id = get_user_open_order(row[0])
                    descuento_pct = int(row[1] or 0)
                    current_app.logger.info('[TBK CALLBACK] order_id=%s descuento_pct=%s', order_id, descuento_pct)
                cur.close()
            if order_id:
                items = get_cart_items(order_id)
                total, _ = get_cart_totals(order_id)
                current_app.logger.info('[TBK CALLBACK] items=%s total=%s', len(items), total)
                cur2 = mysql.connection.cursor()
                for it in items:
                    cur2.execute("UPDATE tools SET stock = GREATEST(stock - %s,0) WHERE id_tool=%s", (it['cantidad'], it['id_tool']))
                    current_app.logger.debug('[TBK CALLBACK] Stock update for id_tool=%s affected=%s', it['id_tool'], cur2.rowcount)
                mysql.connection.commit()
                cur2.close()
                try:
                    finalize_order(order_id, total)
                except Exception:
                    current_app.logger.exception('[TBK CALLBACK] finalize_order failed for order_id=%s', order_id)
                # Asegurar estado completado
                try:
                    curup = mysql.connection.cursor()
                    curup.execute("UPDATE pedidos SET estado_pedido='completado', monto_total=%s WHERE id_pedido=%s", (total, order_id))
                    mysql.connection.commit(); current_app.logger.info('[TBK CALLBACK] pedidos updated rows=%s for id=%s (callback)', curup.rowcount, order_id); curup.close()
                except Exception:
                    mysql.connection.rollback(); current_app.logger.exception('[TBK CALLBACK] Could not ensure pedidos.estado_pedido=completado for order_id=%s', order_id)
                insert_transaction(order_id, total)
                # No borramos items para preservar historial.
                if descuento_pct > 0:
                    cur3 = mysql.connection.cursor()
                    cur3.execute("UPDATE users SET descuento_porcentaje=0 WHERE usuario=%s", (user,))
                    mysql.connection.commit()
                    cur3.close()
            else:
                # Intentar recuperar order_id a partir de la transacción (token)
                try:
                    curtok = mysql.connection.cursor()
                    curtok.execute("SELECT id_pedido FROM transacciones WHERE token=%s", (token_ws,))
                    rowt = curtok.fetchone(); curtok.close()
                    if rowt:
                        order_id = rowt[0]
                        current_app.logger.info('[TBK CALLBACK] Recuperado order_id=%s desde token (callback)', order_id)
                        # Restaurar sesión a partir del pedido
                        try:
                            curp2 = mysql.connection.cursor()
                            curp2.execute("SELECT id_user FROM pedidos WHERE id_pedido=%s", (order_id,))
                            rp = curp2.fetchone(); curp2.close()
                            if rp and rp[0]:
                                uid = rp[0]
                                curu = mysql.connection.cursor()
                                curu.execute("SELECT usuario, COALESCE(role,'') FROM users WHERE id_user=%s", (uid,))
                                ruser = curu.fetchone(); curu.close()
                                if ruser:
                                    try:
                                        session['id_user'] = int(uid)
                                    except Exception:
                                        pass
                                    try:
                                        session['usuario'] = ruser[0]
                                    except Exception:
                                        pass
                                    try:
                                        session['rol'] = (ruser[1] or ('admin' if ruser[0]=='admin' else None))
                                    except Exception:
                                        pass
                                    current_app.logger.info('[TBK CALLBACK] Sesión restaurada para usuario=%s id_user=%s (callback)', ruser[0], uid)
                        except Exception:
                            current_app.logger.exception('[TBK CALLBACK] No se pudo restaurar sesión desde pedido %s (callback)', order_id)
                except Exception:
                    current_app.logger.exception('[TBK CALLBACK] Error buscando transacción token=%s', token_ws)
        except Exception:
            current_app.logger.exception('Fallo procesando pedido tras pago (callback)')
        flash('Gracias por su compra', 'success')
    # Aseguramiento final similar al commit
    try:
        try:
            curchk = mysql.connection.cursor()
            curchk.execute("SELECT id_pedido, status, monto_transaccion FROM transacciones WHERE token=%s", (token_ws,))
            trow = curchk.fetchone(); curchk.close()
            if trow and trow[0]:
                pid = trow[0]
                try:
                    monto_to_set = trow[2] if (trow[2] not in (None, 0)) else None
                    if monto_to_set is not None:
                        curup = mysql.connection.cursor(); curup.execute("UPDATE pedidos SET estado_pedido='completado', monto_total=%s WHERE id_pedido=%s", (monto_to_set, pid)); mysql.connection.commit(); curup.close()
                    else:
                        curup = mysql.connection.cursor(); curup.execute("UPDATE pedidos SET estado_pedido='completado' WHERE id_pedido=%s", (pid,)); mysql.connection.commit(); curup.close()
                    current_app.logger.info('[TBK CALLBACK] Asegurado pedido id=%s estado=completado (via transacciones callback)', pid)
                except Exception:
                    mysql.connection.rollback(); current_app.logger.exception('[TBK CALLBACK] No se pudo asegurar pedido %s desde transacciones (callback)', pid)
        except Exception:
            pass
    except Exception:
        current_app.logger.exception('[TBK CALLBACK] Error en post-check de transacciones para token=%s (callback)', token_ws)
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