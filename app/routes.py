from flask import flash, request, Blueprint, jsonify, render_template, redirect, url_for, session, current_app
from app import app
from .models import (
    fetch_all_tools,
    fetch_tools_by_code,
    insert_tools,
    delete_tools,
    update_tools,
    get_all_users,
    fetch_users_by_id,
    fetch_all_pedidos_ready,
    fetch_pedido_by_id,
    get_usuario_by_usuario,
    fetch_all_pedido,
)
from . import mysql
import random


bp = Blueprint('bp', __name__)

@bp.route('/pedido', methods=['GET'])
def ver_pedido():
    return jsonify(fetch_all_pedido())


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
    return redirect(url_for('bp.carrito'))



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
    return redirect(url_for('bp.carrito'))


@bp.route('/guardar_registro', methods=['POST'])
def guardar_registro():
    usuario_usuario = request.form['usuario_usuario']
    usuario_correo = request.form['usuario_correo'].strip().lower()
    usuario_contraseña = request.form['usuario_contraseña']
    usuario_vercontraseña = request.form['usuario_vercontraseña']

    # Validación formato gmail
    import re
    if not re.match(r'^[A-Za-z0-9._%+-]+@gmail\.com$', usuario_correo):
        flash('El correo debe ser un correo @gmail.com válido.', 'error')
        return redirect(url_for('bp.registro'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT correo FROM users WHERE correo = %s", (usuario_correo,))
    result = cursor.fetchone()
    if result:
        flash('El correo electrónico ya está registrado', 'error')
        cursor.close()
        return redirect(url_for('bp.registro'))
    # Usuario no existe
    if usuario_contraseña == usuario_vercontraseña:
        cursor.execute(
            "INSERT INTO users (correo, contraseña, usuario, descuento) VALUES (%s, %s, %s, %s)",
            (usuario_correo, usuario_contraseña, usuario_usuario, 15)
        )
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('bp.iniciar_sesion'))
    else:
        flash('Las contraseñas no coinciden', 'error')
        cursor.close()
        return redirect(url_for('bp.registro'))




@bp.route('/iniciar_sesion', methods=['POST', 'GET'])
def iniciar_sesion():
    if request.method == 'POST':
        usuario_correo = request.form.get('usuario_correo')
        usuario_contraseña = request.form.get('usuario_contraseña')

        if not usuario_correo or not usuario_contraseña:
            flash('Por favor, ingrese tanto el correo como la contraseña.', 'error')
            return redirect(url_for('bp.iniciar_sesion'))

        # Validación formato gmail
        correo_normalizado = usuario_correo.strip().lower()
        import re
        if not re.match(r'^[A-Za-z0-9._%+-]+@gmail\.com$', correo_normalizado):
            flash('El correo debe ser un correo @gmail.com válido.', 'error')
            return redirect(url_for('bp.iniciar_sesion'))

        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id_user, usuario, descuento FROM users WHERE correo = %s AND contraseña = %s",
            (correo_normalizado, usuario_contraseña)
        )
        result = cursor.fetchone()
        
        if result:
            session['usuario'] = result[1]
            usuario_id = result[0]
            descuento = result[2]

            # Verificar si es un usuario nuevo y asignar un descuento si es necesario
            if descuento == 0:
                pass

            return redirect(url_for('bp.inicio'))
        else:
            flash('Correo y/o contraseña inválidos.', 'error')
            return redirect(url_for('bp.iniciar_sesion'))

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
    return redirect(url_for('bp.inicio'))



@bp.route('/Pedido', methods=['GET'])
def pedido():
    return jsonify(fetch_all_pedidos_ready())

@bp.route('/users', methods=['GET'])
def get_users():
    users = get_all_users()
    return jsonify(users)

# Ruta duplicada eliminada / comentada
# @bp.route('/users', methods=['GET'])
# def get_users_by_id():
#     pass

@bp.route('/tools', methods=['GET'])
def get_tools():
    return jsonify(fetch_all_tools())


@bp.route('/tools/<code>', methods=['GET'])
def get_tool(code):
    return jsonify(fetch_tools_by_code(code))


@bp.route('/tool', methods=['POST'])
def create_tools():
    tools_data = request.get_json(silent=True) or {}
    required = {'id_tool','name'}
    if not required.issubset(tools_data):
        return jsonify({'error':'Faltan campos requeridos'}), 400
    if insert_tools(tools_data):
        return jsonify({'message': 'Herramienta creada exitosamente'}), 201
    return jsonify({'error':'Error al crear herramienta'}), 500


@bp.route('/pedido/<id_pedido>', methods=['GET'])
def get_pedido(id_pedido):
    return jsonify(fetch_pedido_by_id(id_pedido))


@bp.route('/tools/<id>', methods=['DELETE'])
def delete_tool_route(id):
    try:
        if delete_tools(id):
            return jsonify({'message': 'Herramienta eliminada correctamente'}), 200
        return jsonify({'message': 'Herramienta no encontrada'}), 404
    except Exception as e:
        current_app.logger.exception("Error deleting tool")
        return jsonify({'Error': 'Error del servidor'}), 500
    

@bp.route('/tools/<id>', methods=['PUT'])
def update_tool_route(id):
    try:
        tools_data = request.get_json(silent=True) or {}
        if update_tools(id, tools_data):
            return jsonify({'message': 'Herramienta actualizada correctamente'}), 200
        return jsonify({'message': 'Herramienta no encontrada'}), 404
    except Exception as e:
        current_app.logger.exception("Error updating tool")
        return jsonify({'Error': 'Error del servidor'}), 500
    
@bp.route('/')
def main():
    return redirect(url_for('bp.inicio'))

@bp.route('/Cliente')
def cliente():
    usuario = session.get('usuario')
    if not usuario:
        return redirect(url_for('bp.iniciar_sesion'))
    return render_template('Cliente.html', usuario=usuario)


from decimal import Decimal
import pdb


@bp.route('/Carrito')
@bp.route('/carrito')  # alias en minúsculas
def carrito():
    usuario = session.get('usuario')
    try:
        pedidos = fetch_all_pedidos_ready() or []
    except Exception as e:
        current_app.logger.exception('Error obteniendo pedidos')
        pedidos = []

    from decimal import Decimal
    descuento_porcentaje = 0
    descuento_factor = Decimal(0)

    if usuario:
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT descuento FROM users WHERE usuario = %s", (usuario,))
            result = cursor.fetchone()
            if result:
                try:
                    descuento_porcentaje = int(result[0])
                except (ValueError, TypeError):
                    descuento_porcentaje = 0
                descuento_factor = Decimal(descuento_porcentaje) / 100
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    # Calcular subtotal sin descuento y total con descuento de manera segura
    subtotal = Decimal(0)
    for p in pedidos:
        try:
            precio_linea = Decimal(p.get('precio_total') or 0)
        except Exception:
            precio_linea = Decimal(0)
        subtotal += precio_linea

    total_con_descuento = (subtotal * (Decimal(1) - descuento_factor)).quantize(Decimal('1')) if subtotal else Decimal(0)
    payment_available = 'tbk.webpay_plus_create' in app.view_functions

    return render_template(
        'carrito.html',
        pedidos=pedidos,
        usuario=usuario,
        descuento=descuento_porcentaje,
        total_con_descuento=total_con_descuento,
        subtotal=subtotal,
        payment_available=payment_available
    )


@bp.route('/inicio')
def inicio():
    usuario = session.get('usuario')
    return render_template('inicio.html', tools=fetch_all_tools(), usuario=usuario)

@bp.route('/Login') 
def login():
    return render_template('login.html', user=get_all_users())

@bp.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('bp.inicio'))

@bp.route('/Registro')
def registro():
    return render_template('registro.html', user=get_all_users())

# Rutas de categorías eliminadas: navegación ahora mediante anclas en /inicio

# Subcategorías ahora redirigen al ancla dentro de /inicio
def _redir(anchor):
    return redirect(url_for('bp.inicio') + anchor)

@bp.route('/martillos')
def martillos():
    return _redir('#herramientas-manuales')

@bp.route('/destornillador')
def destornillador():
    return _redir('#herramientas-manuales')

@bp.route('/llaves')
def llaves():
    return _redir('#herramientas-manuales')

@bp.route('/electricas')
def electricas():
    return _redir('#herramientas-manuales')

@bp.route('/taladros')
def taladros():
    return _redir('#herramientas-manuales')

@bp.route('/sierras')
def sierras():
    return _redir('#herramientas-manuales')

@bp.route('/lijadoras')
def lijadoras():
    return _redir('#herramientas-manuales')

@bp.route('/materiales')
def materiales():
    return _redir('#materiales-basicos')


def error_page(error):
    return "PÁGINA NO ENCONTRADA..."
app.register_error_handler(404, error_page)


