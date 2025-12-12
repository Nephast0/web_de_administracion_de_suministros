"""Blueprint de inventario y flujo de compras.

Agrupa rutas de catálogo, cesta y menús para separar responsabilidades
respecto a autenticación y reportes.
"""

from decimal import Decimal, InvalidOperation
from sqlalchemy import or_, and_
from flask import abort, Blueprint, current_app as app, flash, redirect, render_template, request, url_for, session, Response
from flask_login import current_user, login_required, logout_user

from ..db import db
from ..forms import EditarPerfilForm
from ..models import CestaDeCompra, Compra, Producto, Proveedor, ActividadUsuario, Usuario
from .helpers import role_required, write_safe_csv_row
from ..services.accounting_services import crear_asiento


inventario_bp = Blueprint("inventario", __name__)
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


def _parse_decimal(value: str | None):
    if not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _build_productos_query(args):
    orden = args.get('orden', 'asc')
    q = (args.get('q') or "").strip()
    tipo = (args.get('tipo') or "").strip()
    marca = (args.get('marca') or "").strip()
    proveedor_id = (args.get('proveedor') or "").strip()
    stock = args.get('stock')
    precio_min = _parse_decimal((args.get('precio_min') or "").strip())
    precio_max = _parse_decimal((args.get('precio_max') or "").strip())

    query = Producto.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Producto.modelo.ilike(like),
                Producto.num_referencia.ilike(like),
                Producto.descripcion.ilike(like),
            )
        )
    if tipo:
        query = query.filter(Producto.tipo_producto.ilike(f"%{tipo}%"))
    if marca:
        query = query.filter(Producto.marca.ilike(f"%{marca}%"))
    if proveedor_id:
        query = query.filter(Producto.proveedor_id == proveedor_id)
    if stock == "bajo":
        query = query.filter(
            and_(
                Producto.cantidad_minima.isnot(None),
                Producto.cantidad <= Producto.cantidad_minima,
            )
        )
    elif stock == "sin":
        query = query.filter(Producto.cantidad <= 0)
    elif stock == "disponible":
        query = query.filter(Producto.cantidad > 0)

    if precio_min is not None:
        query = query.filter(Producto.precio >= precio_min)
    if precio_max is not None:
        query = query.filter(Producto.precio <= precio_max)

    if orden == 'asc':
        query = query.order_by(Producto.modelo.asc())
    elif orden == 'desc':
        query = query.order_by(Producto.modelo.desc())
    elif orden == 'precio_asc':
        query = query.order_by(Producto.precio.asc())
    elif orden == 'precio_desc':
        query = query.order_by(Producto.precio.desc())
    elif orden == 'cantidad_asc':
        query = query.order_by(Producto.cantidad.asc())
    elif orden == 'cantidad_desc':
        query = query.order_by(Producto.cantidad.desc())

    filtros = {
        "q": q,
        "tipo": tipo,
        "marca": marca,
        "proveedor": proveedor_id,
        "stock": stock or "todos",
        "precio_min": args.get('precio_min', ''),
        "precio_max": args.get('precio_max', ''),
        "orden": orden,
    }
    return query, filtros


@inventario_bp.route("/menu_principal", methods=["GET", "POST"])
@login_required
@role_required("admin")
def menu_principal():
    if current_user.is_authenticated and current_user.rol == "admin":
        alertas_stock_bajo = Producto.query.filter(
            and_(
                Producto.cantidad_minima.isnot(None),
                Producto.cantidad <= Producto.cantidad_minima,
            )
        ).count()
        pedidos_pendientes = Compra.query.filter(Compra.estado != "Cancelado").count()
        total_proveedores = Proveedor.query.count()
        total_usuarios = Usuario.query.count()
        total_inventario = Producto.query.count()
        valor_inventario = (
            db.session.query(db.func.sum(Producto.precio * Producto.cantidad)).scalar() or 0
        )
        ventas_totales = db.session.query(db.func.sum(Compra.total)).scalar() or 0

        # Datos de cache/reportes
        try:
            from app.blueprints import reportes as reportes_bp_module  # type: ignore

            cache_ttl = int(getattr(reportes_bp_module, "_CACHE_TTL", 0).total_seconds())
            cache_hits = reportes_bp_module._CACHE_STATS.get("hits", 0)
            cache_misses = reportes_bp_module._CACHE_STATS.get("misses", 0)
        except Exception:
            cache_ttl = app.config.get("REPORT_CACHE_TTL", 0)
            cache_hits = cache_misses = 0
        return render_template(
            "menu_principal.html",
            alertas_stock_bajo=alertas_stock_bajo,
            pedidos_pendientes=pedidos_pendientes,
            total_proveedores=total_proveedores,
            total_usuarios=total_usuarios,
            total_inventario=total_inventario,
            valor_inventario=valor_inventario,
            ventas_totales=ventas_totales,
            cache_ttl=cache_ttl,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )


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
    page = max(int(request.args.get("page", 1)), 1)
    per_page = 10

    if request.method == "GET":
        form.nombre_usuario.data = usuario.nombre
        form.direccion.data = usuario.direccion
        form.currency_locale.data = session.get("currency_locale", "")

    if form.validate_on_submit():
        usuario.nombre = form.nombre_usuario.data
        usuario.direccion = form.direccion.data

        if form.currency_locale.data:
            session["currency_locale"] = form.currency_locale.data

        new_pass = form.new_password.data
        if new_pass:
            current_pass = form.current_password.data
            if not current_pass or not usuario.check_contrasenya(current_pass):
                flash("La contraseña actual no es correcta.", "danger")
                return redirect(url_for("inventario.perfil_cliente"))
            usuario.hash_contrasenya(new_pass)

        try:
            db.session.commit()
            if new_pass:
                logout_user()
                flash("Contraseña actualizada. Vuelve a iniciar sesión.", "success")
                return redirect(url_for("auth.login"))
            flash("Tu perfil ha sido actualizado con éxito.", "success")
            return redirect(url_for("inventario.perfil_cliente", page=page))
        except Exception:
            db.session.rollback()
            flash("Error al actualizar el perfil. Inténtalo nuevamente.", "danger")

    actividades = []
    if hasattr(usuario, "actividades"):
        actividades = sorted(usuario.actividades, key=lambda a: a.fecha, reverse=True)
    total = len(actividades)
    start = (page - 1) * per_page
    end = start + per_page
    actividades_page = actividades[start:end]

    return render_template(
        "perfil-cliente.html",
        form=form,
        usuario=usuario,
        actividades=actividades_page,
        pagina=page,
        total_actividades=total,
    )


@inventario_bp.route("/productos", methods=["GET", "POST"])
@login_required
@role_required("admin")
def productos():
    query, filtros = _build_productos_query(request.args)
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("page_size", DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    productos = pagination.items
    alertas = [
        producto for producto in productos
        if producto.cantidad_minima is not None
        and producto.cantidad is not None
        and producto.cantidad <= producto.cantidad_minima
    ]
    proveedores = Proveedor.query.all()
    return render_template(
        'inventario_admin.html',
        productos=productos,
        orden=filtros["orden"],
        alertas=alertas,
        proveedores=proveedores,
        filtros=filtros,
        pagination=pagination,
    )


@inventario_bp.route('/productos/export', methods=['GET'])
@login_required
@role_required("admin")
def exportar_productos():
    query, _ = _build_productos_query(request.args)
    productos = query.all()
    import csv, io
    si = io.StringIO()
    cw = csv.writer(si)
    write_safe_csv_row(cw, ['Tipo', 'Marca', 'Modelo', 'Descripcion', 'Precio', 'Cantidad', 'Proveedor'])
    for p in productos:
        write_safe_csv_row(
            cw,
            [
                p.tipo_producto,
                p.marca,
                p.modelo,
                p.descripcion,
                p.precio,
                p.cantidad,
                p.proveedor_id,
            ],
        )
    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers['Content-Disposition'] = 'attachment; filename=productos.csv'
    return output


@inventario_bp.route("/productos_cliente", methods=["GET", "POST"])
@login_required
@role_required("cliente")
def productos_cliente():
    query, filtros = _build_productos_query(request.args)
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("page_size", DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    productos = pagination.items
    alertas = [
        producto
        for producto in productos
        if producto.cantidad_minima is not None
        and producto.cantidad is not None
        and producto.cantidad <= producto.cantidad_minima
    ]
    return render_template(
        "productos-cliente.html",
        productos=productos,
        alertas=alertas,
        filtros=filtros,
        pagination=pagination,
    )


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
    return render_template('cesta.html', items=items, cesta_items=items, total=total)


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
    direccion = (request.form.get('direccion') or "").strip()
    metodo_pago = (request.form.get('metodo_pago') or "").strip()

    if not direccion or not metodo_pago:
        flash('Por favor, completa todos los campos', 'warning')
        return redirect(url_for('inventario.confirmacion_de_compra'))

    if len(direccion) > 255 or len(metodo_pago) > 50:
        flash('Los campos exceden la longitud permitida.', 'warning')
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
                # Nota: No actualizamos asientos de compras existentes para simplificar,
                # idealmente cada compra debería ser única o generar su propio asiento.
                # Asumiremos que se crea un asiento por el delta.
                # Para simplificar, crearemos asiento por el total añadido.
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
            
            # --- Contabilidad ---
            # 1. Ingreso por Venta
            # Debe: Caja (570) - Haber: Ventas (700)
            crear_asiento(
                descripcion=f"Venta de {producto.modelo} (x{cantidad})",
                usuario_id=current_user.id,
                referencia_id=producto_id,
                apuntes_data=[
                    {'cuenta_codigo': '570', 'debe': total, 'haber': 0},
                    {'cuenta_codigo': '700', 'debe': 0, 'haber': total}
                ]
            )
            
            # 2. Costo de Venta (Salida de Inventario)
            # Debe: Costo de Mercaderías (600) - Haber: Inventario (300)
            costo_total = Decimal(producto.costo) * Decimal(cantidad)
            if costo_total > 0:
                crear_asiento(
                    descripcion=f"Costo Venta {producto.modelo}",
                    usuario_id=current_user.id,
                    referencia_id=producto_id,
                    apuntes_data=[
                        {'cuenta_codigo': '600', 'debe': costo_total, 'haber': 0},
                        {'cuenta_codigo': '300', 'debe': 0, 'haber': costo_total}
                    ]
                )

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
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("page_size", DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
    pagination = (
        Compra.query.filter_by(usuario_id=current_user.id)
        .filter(Compra.estado != "Cancelado")
        .order_by(Compra.fecha.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return render_template("pedidos.html", pedidos=pagination.items, pagination=pagination)


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
            
            # --- Contabilidad (Reversión) ---
            # 1. Revertir Ingreso
            crear_asiento(
                descripcion=f"Cancelación Venta {producto.modelo}",
                usuario_id=current_user.id,
                referencia_id=pedido.id,
                apuntes_data=[
                    {'cuenta_codigo': '700', 'debe': pedido.total, 'haber': 0},
                    {'cuenta_codigo': '570', 'debe': 0, 'haber': pedido.total}
                ]
            )
            
            # 2. Revertir Costo
            costo_total = Decimal(producto.costo) * Decimal(pedido.cantidad)
            if costo_total > 0:
                crear_asiento(
                    descripcion=f"Reversión Costo {producto.modelo}",
                    usuario_id=current_user.id,
                    referencia_id=pedido.id,
                    apuntes_data=[
                        {'cuenta_codigo': '300', 'debe': costo_total, 'haber': 0},
                        {'cuenta_codigo': '600', 'debe': 0, 'haber': costo_total}
                    ]
                )

        pedido.estado = "Cancelado"

        db.session.commit()
        flash('Pedido cancelado y cantidad devuelta al inventario', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al cancelar el pedido', 'danger')
        app.logger.exception("Error al cancelar pedido %s", pedido_id)

    return redirect(url_for('inventario.pedidos'))
