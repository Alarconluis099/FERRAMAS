from flask import flash, request, Blueprint, jsonify, render_template, redirect, url_for, session
from app import app
from .models import fetch_all_tools, fetch_tools_by_code, insert_tools, delete_tools, update_tools, get_all_users, fetch_users_by_id, fetch_all_pedidos_ready, fetch_pedido_by_id, get_usuario_by_usuario, fetch_all_pedido
from . import mysql
import random


bp = Blueprint('bp', __name__)

@bp.route('/pedido', methods=['GET'])
def ver_pedido():
    pedido = fetch_all_pedido()
    return jsonify(pedido)


@bp.route('/disminuir_cantidad/<int:id_pedido>', methods=['POST'])
def disminuir_cantidad(id_pedido):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT cantidad FROM pedido WHERE id_pedido = %s", (id_pedido,))
    result = cursor.fetchone()

    if result:
        cantidad = result[0]
        if cantidad > 1:
            nueva_cantidad = cantidad - 1
            cursor.execute(
                "UPDATE pedido SET cantidad = %s WHERE id_pedido = %s",
                (nueva_cantidad, id_pedido)
            )
        else:
            cursor.execute("DELETE FROM pedido WHERE id_pedido = %s", (id_pedido,))

        mysql.connection.commit()

    cursor.close()
    return redirect(url_for('carrito'))



@bp.route('/aumentar_cantidad/<int:product_id>', methods=['POST'])
def aumentar_cantidad(product_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT cantidad FROM pedido WHERE id_pedido = %s", (product_id,))
    result = cursor.fetchone()

    if result:
        cantidad = result[0]
        if cantidad >= 1:
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


@bp.route('/guardar_registro', methods=['POST'])
def guardar_registro():
    usuario_usuario = request.form['usuario_usuario']
    usuario_correo = request.form['usuario_correo']
    usuario_contraseña = request.form['usuario_contraseña']
    usuario_vercontraseña = request.form['usuario_vercontraseña']

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT correo FROM users WHERE correo = %s", (usuario_correo,))
    result = cursor.fetchone()

    if result:
        # El usuario ya existe
        flash('El correo electrónico ya está registrado', 'error')
        return redirect(url_for('registro'))  # O redirigir a la página de inicio de sesión
    else:
        # El usuario no existe, proceder con el registro
        if usuario_contraseña == usuario_vercontraseña:
            # Insertar el nuevo usuario en la base de datos con un descuento predeterminado de 0.0
            cursor.execute("INSERT INTO users (correo, contraseña, usuario, descuento) VALUES (%s, %s, %s, %s)", (usuario_correo, usuario_contraseña, usuario_usuario, 15))
            mysql.connection.commit()

            cursor.close()
            return redirect(url_for('iniciar_sesion'))
        else:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('registro'))




@bp.route('/iniciar_sesion', methods=['POST', 'GET'])
def iniciar_sesion():
    if request.method == 'POST':
        usuario_correo = request.form.get('usuario_correo')
        usuario_contraseña = request.form.get('usuario_contraseña')

        if not usuario_correo or not usuario_contraseña:
            flash('Por favor, ingrese tanto el correo como la contraseña.', 'error')
            return redirect(url_for('iniciar_sesion'))

        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id_user, usuario, descuento FROM users WHERE correo = %s AND contraseña = %s",
            (usuario_correo, usuario_contraseña)
        )
        result = cursor.fetchone()
        
        if result:
            session['usuario'] = result[1]
            usuario_id = result[0]
            descuento = result[2]

            # Verificar si es un usuario nuevo y asignar un descuento si es necesario
            if descuento == 0:
                pass

            return render_template('inicio')  # Redirige a la página de inicio después de iniciar sesión
        else:
            flash('Correo y/o contraseña inválidos.', 'error')
            return redirect(url_for('iniciar_sesion'))

    return render_template('login.html')


    

@bp.route('/guardar_pedido', methods=['POST'])
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
    return render_template('inicio')



@bp.route('/Pedido', methods=['GET'])
def pedido():
    pedido = fetch_all_pedidos_ready()
    return jsonify(pedido)

@bp.route('/users', methods=['GET'])
def get_users():
    users = get_all_users()
    return jsonify(users)

@bp.route('/users', methods=['GET'])
def get_users_by_id():
    users = fetch_users_by_id()
    return jsonify(users)

@app.route('/tools', methods=['GET'])
def get_tools():
    tools = fetch_all_tools()
    return jsonify(tools)


@bp.route('/tools/<code>', methods=['GET'])
def get_tool(code):
    tool = fetch_tools_by_code(code)
    return jsonify(tool)


@bp.route('/tool', methods=['POST'])
def create_tools():
    tools_data = request.get_json()
    insert_tools(tools_data)
    return jsonify({'message': 'Herramienta creada exitosamente'}), 200


@bp.route('/pedido/<id_pedido>', methods=['GET'])
def get_pedido(id_pedido):
    pedido = fetch_pedido_by_id(id_pedido)
    return jsonify(pedido)


@bp.route('/tools/<id>', methods=['DELETE'])
def delete_tool_route(id):
    try:
        eliminada = delete_tools(id)

        if eliminada:
            return jsonify({'message': 'Herramienta eliminada correctamente'}), 200
        else:
            return jsonify({'message': 'Herramienta no encontrada'}), 404
    except Exception:
        return jsonify({'Error': 'Error del servidor'}), 500
    

@bp.route('/tools/<id>', methods=['PUT'])
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
    
@bp.route('/')
def main():
    return redirect(url_for('inicio'))

@bp.route('/Cliente')
def cliente():
    usuario = session.get('usuario')
    if not usuario:
        return redirect(url_for('iniciar_sesion'))
    return render_template('Cliente.html', usuario=usuario)


from decimal import Decimal
import pdb


@bp.route('/Carrito')
def carrito():
    usuario = session.get('usuario')
    pedidos = fetch_all_pedidos_ready() 

    descuento = Decimal(0)
    if usuario:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT descuento FROM users WHERE usuario = %s", (usuario,))
        result = cursor.fetchone()
        if result:
            descuento = Decimal(result[0]) / 100

    pedidos_agrupados = {}
    for pedido in pedidos:
        id_pedido = pedido['id_pedido']
        if id_pedido not in pedidos_agrupados:
            pedidos_agrupados[id_pedido] = {
                'precio_pedido': pedido['precio_pedido'],
                'cantidad_total': 0,
                'id_pedido': id_pedido,
                'nom_pedido': pedido['nom_pedido'],
                'desc_pedido': pedido['desc_pedido']
            }
        pedidos_agrupados[id_pedido]['cantidad_total'] += pedido['cantidad_total']

    total_con_descuento = sum(
        Decimal(pedido['precio_pedido']) * pedido['cantidad_total'] * (1 - descuento)
        for pedido in pedidos_agrupados.values()
    )

    return render_template(
        'carrito.html',
        pedidos=list(pedidos_agrupados.values()),
        usuario=usuario,
        descuento=descuento,
        total_con_descuento=total_con_descuento
    )


@bp.route('/inicio')
def inicio():
    usuario = session.get('usuario')
    tools = fetch_all_tools()
    return render_template('inicio.html', tools=tools, usuario=usuario)

@bp.route('/Login') 
def login():
    user = get_all_users()
    return render_template('login.html', user=user)

@bp.route('/logout')
def logout():
    # Eliminar la información de la sesión del usuario
    session.pop('usuario', None)
    # Redirigir al usuario a la página de inicio de sesión o página principal
    return render_template('inicio')

@bp.route('/Registro')
def registro():
    user = get_all_users()
    return render_template('registro.html', user=user)

@bp.route('/Equipos_medicion')
def equipos_medicion():
    usuario=session.get('usuarios') 
    return render_template('equipos-medicion.html',usuario=usuario)  
    

@bp.route('/Equipos_seguridad')
def equipos_seguridad():
    usuario=session.get('usuarios')
    return render_template('equipos-seguridad.html',usuario=usuario)

@bp.route('/Fijaciones_adhesivos')
def fijaciones_adhesivos():
    usuario=session.get('usuarios')
    return render_template('fijaciones-adhesivos.html',usuario=usuario)

@bp.route('/Herramientas_manuales')
def herramientas_manuales():
    usuario=session.get('usuarios')
    return render_template('herramientas-manuales.html',usuario=usuario)

@bp.route('/Materiales_basicos')
def materiales_basicos():
    usuario=session.get('usuarios')
    return render_template('materiales-basicos.html',usuario=usuario)

@bp.route('/Tornillos_anclajes')
def tornillos_anclajes():
    usuario=session.get('usuarios')
    return render_template('tornillos-anclajes.html',usuario=usuario)

# Herramientas manuales - Subcategorias

@bp.route('/martillos')
def martillos():
    return render_template('HM-martillos.html')

@bp.route('/destornillador')
def destornillador():
    return render_template('HM-destornillador.html')

@bp.route('/llaves')
def llaves():
    return render_template('HM-llaves.html')

@bp.route('/electricas')
def electricas():
    return render_template('HM-electricas.html')

bp.route('/taladros')
def taladros():
    return render_template('HM-taladros.html')

bp.route('/sierras')
def sierras():
    return render_template('HM-sierras.html')

bp.route('/lijadoras')
def lijadoras():
    return render_template('HM-lijadoras.html')

bp.route('/materiales')
def materiales():
    return render_template('HM-materiales.html')


def error_page(error):
    return "PÁGINA NO ENCONTRADA..."
app.register_error_handler(404, error_page)


