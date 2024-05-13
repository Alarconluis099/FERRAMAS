from flask import Flask, jsonify, request
from transbank.webpay import Webpay, Transaction, Options
from src import src 

Webpay.configure_for_testing()

@src.route('/init_transaction', methods=['POST'])
def init_transaction():
    amount = request.json['amount']
    buy_order = '123456'  # Reemplaza '123456' con tu propio número de orden de compra
    session_id = 'sesion123456'  # Reemplaza 'sesion123456' con tu propio ID de sesión
    return_url = 'http://localhost:5000/commit'  # Reemplaza 'http://localhost:5000/commit' con tu propia URL de retorno
    tx = Transaction(Options(123456, '123456789', 'TEST'))  # Reemplaza los valores con tus propias credenciales
    response = tx.create(buy_order, session_id, amount, return_url)
    return jsonify(response)

@src.route('/commit', methods=['POST'])
def commit():
    token = request.json['token_ws']
    tx = Transaction(Options(123456, '123456789', 'TEST'))  # Reemplaza los valores con tus propias credenciales
    response = tx.commit(token)
    return jsonify(response)

@src.route('/abort', methods=['POST'])
def abort():
    token = request.json['token_ws']
    tx = Transaction(Options(123456, '123456789', 'TEST'))  # Reemplaza los valores con tus propias credenciales
    response = tx.refund(token, 1000)  # Amount to refund
    return jsonify(response)

