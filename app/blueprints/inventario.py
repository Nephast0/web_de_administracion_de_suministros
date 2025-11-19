"""Blueprint de inventario y flujo de compras.

Agrupa rutas de catálogo, cesta y menús para separar responsabilidades
respecto a autenticación y reportes.
"""

from flask import abort, Blueprint, current_app as app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..db import db
from ..forms import EditarPerfilForm
from ..models import CestaDeCompra, Compra, Producto, Proveedor
from .helpers import role_required


inventario_bp = Blueprint("inventario", __name__)


@inventario_bp.route("/menu_principal", methods=["GET", "POST"])
@login_required
@role_required("admin")
def menu_principal():
    if current_user.is_authenticated and current_user.rol == "admin":
        return render_template("menu_principal.html")


@inventario_bp.route("/menu-cliente", methods=["GET", "POST"])
@login_required
@role_required("cliente")
def menu_cliente():
    if current_user.is_authenticated and current_user.rol == "cliente":  # Verifica que el rol sea Cliente
        return render_template("menu-cliente.html")  # Renderiza el menú del cliente


@inventario_bp.route("/perfil_cliente", methods=["GET", "POST"])
@login_required
@role_required("cliente")
def perfil_cliente():
    usuario = current_user
    form = EditarPerfilForm()

    if request.method == "GET":
        form.nombre_usuario.data = usuario.nombre
        form.direccion.data = usuario.direccion

    if form.validate_on_submit():
        usuario.nombre = form.nombre_usuario.data
        usuario.direccion = form.direccion.data

        try:
            db.session.commit()
            flash("Tu perfil ha sido actualizado con éxito.", "success")
            return redirect(url_for("inventario.perfil_cliente"))
        except Exception:
            db.session.rollback()
            flash("Error al actualizar el perfil. Inténtalo nuevamente.", "danger")

    return render_template("perfil-cliente.html", form=form, usuario=usuario)


@inventario_bp.route("/productos", methods=["GET", "POST"])
@login_required
@role_required("admin")
def productos():
    orden = request.args.get('orden', 'asc')
    if orden == 'asc':
        productos = Producto.query.order_by(Producto.modelo.asc()).all()
    elif orden == 'desc':
        productos = Producto.query.order_by(Producto.modelo.desc()).all()
    elif orden == 'precio_asc':
        productos = Producto.query.order_by(Producto.precio.asc()).all()
    elif orden == 'precio_desc':
        productos = Producto.query.order_by(Producto.precio.desc()).all()
    elif orden == 'cantidad_asc':
        productos = Producto.query.order_by(Producto.cantidad.asc()).all()
    elif orden == 'cantidad_desc':
        productos = Producto.query.order_by(Producto.cantidad.desc()).all()
    else:
        productos = Producto.query.all()
    # Alertamos al administrador cuando el producto alcanzó el umbral mínimo
    alertas = [
        producto for producto in productos
        if producto.cantidad_minima is not None
        and producto.cantidad is not None
        and producto.cantidad <= producto.cantidad_minima
    ]
    return render_template('inventario_admin.html', productos=productos, orden=orden, alertas=alertas)


@inventario_bp.route("/productos_cliente", methods=["GET", "POST"])
@login_required
@role_required("cliente")
def productos_cliente():
    productos = Producto.query.all()
    alertas = [producto for producto in productos if producto.cantidad <= producto.cantidad_minima]
    return render_template("productos-cliente.html", productos=productos, alertas=alertas)


@inventario_bp.route('/agregar_a_la_cesta/<producto_id>', methods=['POST'])
@login_required
@role_required("cliente")
def agregar_a_la_cesta(producto_id):
    # db.session.get evita los warnings de la API legacy y permite controlar el 404 de forma explícita.
    producto = db.session.get(Producto, producto_id)
    if not producto:
        abort(404, description="Producto no encontrado")

    raw_cantidad = request.form.get('cantidad', 1)
    try:
        cantidad = int(raw_cantidad)
    except (TypeError, ValueError):
        flash('Cantidad inválida.', 'warning')
        return redirect(url_for('inventario.productos_cliente'))

    if cantidad < 1:
        flash('La cantidad debe ser al menos 1.', 'warning')
        return redirect(url_for('inventario.productos_cliente'))

    item_en_cesta = CestaDeCompra.query.filter_by(usuario_id=current_user.id, producto_id=producto.id).first()

    if item_en_cesta:
        item_en_cesta.cantidad += cantidad
        flash(f'Se agregó {cantidad} más de {producto.modelo} a tu cesta', 'success')
    else:
        nuevo_item = CestaDeCompra(usuario_id=current_user.id, producto_id=producto.id, cantidad=cantidad)
        db.session.add(nuevo_item)
        flash(f'{producto.modelo} ha sido agregado a tu cesta', 'success')

    db.session.commit()
    return redirect(url_for('inventario.productos_cliente'))


@inventario_bp.route("/cesta", methods=['POST', 'GET'])
@login_required
@role_required("cliente")
def cesta():
    items = CestaDeCompra.query.filter_by(usuario_id=current_user.id).all()
    total = sum(item.producto.precio * item.cantidad for item in items)
    return render_template('cesta.html', items=items, total=total)


@inventario_bp.route('/actualizar_cesta/<item_id>', methods=['POST'])
@login_required
@role_required("cliente")
def actualizar_cesta(item_id):
    item = db.session.get(CestaDeCompra, item_id)
    if not item:
        abort(404, description="Elemento no encontrado en la cesta")

    try:
        nueva_cantidad = int(request.form.get('cantidad'))
    except (TypeError, ValueError):
        flash('Cantidad inválida.', 'warning')
        return redirect(url_for('inventario.cesta'))

    if nueva_cantidad < 1:
        flash('La cantidad debe ser al menos 1.', 'warning')
        return redirect(url_for('inventario.cesta'))

    item.cantidad = nueva_cantidad
    db.session.commit()
    flash('Cantidad actualizada.', 'success')
    return redirect(url_for('inventario.cesta'))


@inventario_bp.route('/eliminar_de_la_cesta/<item_id>', methods=['POST'])
@login_required
@role_required("cliente")
def eliminar_de_la_cesta(item_id):
    item = db.session.get(CestaDeCompra, item_id)

    if item and item.usuario_id == current_user.id:
        db.session.delete(item)
        db.session.commit()

    return redirect(url_for('inventario.cesta'))


@inventario_bp.route('/confirmacion-de-compra', methods=['GET', 'POST'])
@login_required
@role_required("cliente")
def confirmacion_de_compra():
    cesta_items = CestaDeCompra.query.filter_by(usuario_id=current_user.id).all()
    total = sum(item.producto.precio * item.cantidad for item in cesta_items)

    return render_template('confirmacion-de-compra.html', cesta_items=cesta_items, total=total)


@inventario_bp.route('/confirmar-compra', methods=['POST'])
@login_required
@role_required("cliente")
def confirmar_compra():
    direccion = request.form.get('direccion')
    metodo_pago = request.form.get('metodo_pago')

    if not direccion or not metodo_pago:
        flash('Por favor, completa todos los campos', 'warning')
        return redirect(url_for('inventario.confirmacion_de_compra'))

    cesta_items = CestaDeCompra.query.filter_by(usuario_id=current_user.id).all()

    if not cesta_items:
        flash('No hay productos en la cesta', 'warning')
        return redirect(url_for('inventario.cesta'))

    try:
        pedidos = {}

        for item in cesta_items:
            producto = db.session.get(Producto, item.producto_id)
            if not producto:
                flash('Uno de los productos ya no está disponible.', 'warning')
                return redirect(url_for('inventario.cesta'))

            proveedor_id = producto.proveedor_id
            if item.producto_id in pedidos:
                pedidos[item.producto_id]['cantidad'] += item.cantidad
            else:
                pedidos[item.producto_id] = {
                    'producto': producto,
                    'cantidad': item.cantidad,
                    'precio_unitario': producto.precio,
                    'proveedor_id': proveedor_id
                }

        for data in pedidos.values():
            if data['producto'].cantidad < data['cantidad']:
                flash(f"No hay suficiente inventario para {data['producto'].modelo}", 'danger')
                return redirect(url_for('inventario.cesta'))

        for producto_id, data in pedidos.items():
            producto = data['producto']
            cantidad = data['cantidad']
            precio_unitario = data['precio_unitario']
            proveedor_id = data['proveedor_id']
            total = cantidad * precio_unitario

            producto.cantidad -= cantidad

            compra_existente = Compra.query.filter_by(
                producto_id=producto_id,
                usuario_id=current_user.id,
                estado="Pendiente",
            ).first()

            if compra_existente:
                compra_existente.cantidad += cantidad
                compra_existente.total += total
            else:
                nueva_compra = Compra(
                    producto_id=producto_id,
                    usuario_id=current_user.id,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    proveedor_id=proveedor_id,
                    total=total,
                    estado="Pendiente"
                )
                db.session.add(nueva_compra)

        for item in cesta_items:
            db.session.delete(item)

        db.session.commit()

        flash('Compra realizada con éxito', 'success')
        return redirect(url_for('inventario.pedidos'))
    except Exception:
        db.session.rollback()
        app.logger.exception("Error al realizar la compra para el usuario %s", current_user.id)
        flash('Error al realizar la compra', 'danger')
        return redirect(url_for('inventario.cesta'))


@inventario_bp.route("/pedidos", methods=["GET"])
@login_required
@role_required("cliente")
def pedidos():
    pedidos = Compra.query.filter_by(usuario_id=current_user.id).filter(Compra.estado != "Cancelado").all()
    return render_template("pedidos.html", pedidos=pedidos)


@inventario_bp.route('/cancelar_pedido/<pedido_id>', methods=['POST'])
@login_required
@role_required("cliente")
def cancelar_pedido(pedido_id):
    pedido = db.session.get(Compra, pedido_id)

    if not pedido or pedido.usuario_id != current_user.id:
        flash('Pedido no encontrado o no tienes permiso para cancelarlo', 'danger')
        return redirect(url_for('inventario.pedidos'))

    try:
        producto = db.session.get(Producto, pedido.producto_id)
        if producto:
            producto.cantidad += pedido.cantidad

        pedido.estado = "Cancelado"

        db.session.commit()
        flash('Pedido cancelado y cantidad devuelta al inventario', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al cancelar el pedido', 'danger')
        app.logger.exception("Error al cancelar pedido %s", pedido_id)

    return redirect(url_for('inventario.pedidos'))
