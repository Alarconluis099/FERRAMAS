from config import appConfig
from flask import request, jsonify, render_template 
from app import mysql

def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE correo = %s AND contraseña = %s", (correo, contraseña))
        user = cur.fetchone()
        if user:
            return jsonify({'status': 'success', 'message': 'Login successful', 'user': user})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid correo or contraseña'})
    return render_template('login.html')
    