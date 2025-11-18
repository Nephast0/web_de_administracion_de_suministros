"""Blueprint de reportes y endpoints de datos agregados."""

from collections import defaultdict
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import func

from ..db import db
from ..models import Compra, Producto, Usuario
from .helpers import _period_key_and_label, role_required


reportes_bp = Blueprint("reportes", __name__)


@reportes_bp.route('/graficas', methods=["GET"])
@login_required
@role_required("admin")
def graficas():
    return render_template("graficas.html")


@reportes_bp.route('/data/distribucion_productos')
@login_required
@role_required("admin")
def data_distribucion_productos():
    productos = (
        db.session.query(Producto.tipo_producto, func.count(Producto.id))
        .group_by(Producto.tipo_producto)
        .order_by(Producto.tipo_producto)
        .all()
    )
    tipos = [producto.tipo_producto for producto in productos]
    cantidades = [producto[1] for producto in productos]
    return jsonify({'tipos': tipos, 'cantidades': cantidades})


@reportes_bp.route('/data/ventas_totales')
@login_required
@role_required("admin")
def data_ventas_totales():
    intervalo = request.args.get('interval', 'mes')
    ventas_totales = defaultdict(float)
    orden = {}
    etiqueta_periodo = None
    for compra in Compra.query.all():
        clave, label, etiqueta_periodo = _period_key_and_label(compra.fecha, intervalo)
        ventas_totales[label] += float(compra.total or 0)
        orden[label] = clave

    if etiqueta_periodo is None:
        _, _, etiqueta_periodo = _period_key_and_label(datetime.utcnow(), intervalo)

    periodos = [label for label, _ in sorted(orden.items(), key=lambda item: item[1])]
    totales = [ventas_totales[label] for label in periodos]

    return jsonify({'periodos': periodos, 'totales': totales, 'period_label': etiqueta_periodo})


@reportes_bp.route('/data/productos_mas_vendidos')
@login_required
@role_required("admin")
def data_productos_mas_vendidos():
    ventas = (
        db.session.query(Producto.modelo, func.sum(Compra.cantidad).label('cantidad'))
        .join(Producto, Producto.id == Compra.producto_id)
        .group_by(Producto.id)
        .order_by(func.sum(Compra.cantidad).desc())
        .limit(10)
        .all()
    )

    productos = [venta[0] for venta in ventas]
    cantidades = [venta[1] for venta in ventas]
    return jsonify({'productos': productos, 'cantidades': cantidades})


@reportes_bp.route('/data/usuarios_registrados')
@login_required
@role_required("admin")
def data_usuarios_registrados():
    intervalo = request.args.get('interval', 'mes')
    if intervalo not in {"dia", "semana", "mes", "trimestre", "anio"}:
        return jsonify({'error': 'Intervalo no válido'}), 400

    totales = defaultdict(int)
    orden = {}
    for usuario in Usuario.query.order_by(Usuario.fecha_registro.asc()).all():
        clave, label, _ = _period_key_and_label(usuario.fecha_registro, intervalo)
        totales[label] += 1
        orden[label] = clave

    periodos = [label for label, _ in sorted(orden.items(), key=lambda item: item[1])]
    conteos = [totales[label] for label in periodos]

    return jsonify({'periodos': periodos, 'totales': conteos})


@reportes_bp.route('/data/ingresos_por_usuario')
@login_required
@role_required("admin")
def data_ingresos_por_usuario():
    intervalo = request.args.get('interval', 'mes')
    ingresos = defaultdict(float)
    orden = {}
    for compra, usuario in db.session.query(Compra, Usuario).join(Usuario, Usuario.id == Compra.usuario_id).all():
        clave, periodo_label, _ = _period_key_and_label(compra.fecha, intervalo)
        key = (usuario.usuario, periodo_label)
        ingresos[key] += float(compra.total or 0)
        orden[key] = (usuario.usuario, *clave)

    ordered_keys = [key for key, _ in sorted(orden.items(), key=lambda item: item[1])]
    usuarios = [f"{usuario} ({periodo})" for (usuario, periodo) in ordered_keys]
    totales = [ingresos[(usuario, periodo)] for (usuario, periodo) in ordered_keys]

    return jsonify({'usuarios': usuarios, 'ingresos': totales})


@reportes_bp.route('/data/compras_por_categoria')
@login_required
@role_required("admin")
def data_compras_por_categoria():
    compras = db.session.query(
        Producto.tipo_producto,
        func.count(Compra.id).label('total')
    ).join(Compra).group_by(Producto.tipo_producto).all()
    categorias = [compra.tipo_producto for compra in compras]
    totales = [compra.total for compra in compras]
    return jsonify({'categorias': categorias, 'compras': totales})


@reportes_bp.route('/data/productos_menos_vendidos')
@login_required
@role_required("admin")
def data_productos_menos_vendidos():
    ventas = db.session.query(
        Compra.producto_id,
        func.sum(Compra.cantidad).label('cantidad')
    ).group_by(Compra.producto_id).order_by(func.sum(Compra.cantidad).asc()).limit(10).all()

    productos = [db.session.query(Producto).get(venta.producto_id).modelo for venta in ventas]
    cantidades = [venta.cantidad for venta in ventas]
    return jsonify({'productos': productos, 'cantidades': cantidades})


@reportes_bp.route("/graficas_cliente", methods=["GET"])
@login_required
@role_required("cliente")
def graficas_cliente():
    return render_template("graficas-cliente.html")
