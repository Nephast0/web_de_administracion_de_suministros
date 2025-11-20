"""Blueprint de reportes y endpoints de datos agregados."""

import json
import logging
import os
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from ..db import db
from ..models import Compra, Producto, Usuario
from .helpers import _period_key_and_label, role_required


reportes_bp = Blueprint("reportes", __name__)
_logger = logging.getLogger(__name__)
_VALID_INTERVALS = {"dia", "semana", "mes", "trimestre", "anio"}
_CACHE: dict[str, dict] = {}
_CACHE_STATS = {"hits": 0, "misses": 0}
_CACHE_HISTORY: deque[dict] = deque(maxlen=50)
_DEFAULT_CACHE_TTL = int(os.getenv("REPORT_CACHE_TTL", "60"))
_CACHE_TTL = timedelta(seconds=_DEFAULT_CACHE_TTL)
_CACHE_FILE_FALLBACK = Path(__file__).resolve().parents[2] / "instance" / "report_cache.json"


def _make_cache_key(prefix: str, **params) -> str:
    """Genera una clave estable para almacenar respuestas JSON en memoria."""

    serialized = "|".join(f"{key}:{params[key]}" for key in sorted(params))
    return f"{prefix}|{serialized}"


def _get_cache_file() -> Path:
    override = current_app.config.get("REPORT_CACHE_FILE") or os.getenv("REPORT_CACHE_FILE")
    if override:
        return Path(override)
    return _CACHE_FILE_FALLBACK


def _load_cache_settings():
    global _CACHE_TTL
    path = _get_cache_file()
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        seconds = int(data.get("ttl_seconds", _DEFAULT_CACHE_TTL))
        _CACHE_TTL = timedelta(seconds=seconds)
        _logger.info("cache-config-loaded ttl=%s", seconds)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        _logger.warning("No se pudo cargar la configuración de caché: %s", exc)


def _persist_cache_settings(seconds: int):
    path = _get_cache_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ttl_seconds": seconds, "updated_at": datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _record_cache_event(event_type: str, **extra):
    _CACHE_HISTORY.appendleft(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            **extra,
        }
    )


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if not entry:
        _CACHE_STATS["misses"] += 1
        _record_cache_event("miss", key=key)
        return None
    if entry["expires"] < datetime.now(timezone.utc):
        _CACHE.pop(key, None)
        _CACHE_STATS["misses"] += 1
        _record_cache_event("miss", key=f"{key} (expired)")
        return None
    _CACHE_STATS["hits"] += 1
    _record_cache_event("hit", key=key)
    return entry["data"]


def _cache_set(key: str, data):
    _CACHE[key] = {
        "data": data,
        "expires": datetime.now(timezone.utc) + _CACHE_TTL,
    }


def _cached_json(key: str, builder):
    payload = _cache_get(key)
    if payload is not None:
        _logger.info("cache-hit endpoint=%s hits=%s misses=%s", key, _CACHE_STATS["hits"], _CACHE_STATS["misses"])
        return jsonify(payload)
    payload = builder()
    _cache_set(key, payload)
    _logger.info("cache-miss endpoint=%s hits=%s misses=%s", key, _CACHE_STATS["hits"], _CACHE_STATS["misses"])
    return jsonify(payload)


@reportes_bp.route("/data/cache_stats")
@login_required
@role_required("admin")
def cache_stats():
    """Expone métricas simples de cache para monitoreo manual."""

    return jsonify({
        "entries": len(_CACHE),
        "hits": _CACHE_STATS["hits"],
        "misses": _CACHE_STATS["misses"],
        "ttl_seconds": _CACHE_TTL.total_seconds(),
    })


@reportes_bp.route("/data/cache_history")
@login_required
@role_required("admin")
def cache_history():
    """Devuelve los últimos eventos registrados en la caché."""

    return jsonify({"events": list(_CACHE_HISTORY)})


@reportes_bp.route("/data/cache_ttl", methods=["POST"])
@login_required
@role_required("admin")
def update_cache_ttl():
    """Permite ajustar dinámicamente el TTL de la caché desde la UI."""

    global _CACHE_TTL

    payload = request.get_json(silent=True) or request.form
    raw_seconds = payload.get("ttl_seconds") or payload.get("ttl")
    try:
        seconds = int(raw_seconds)
    except (TypeError, ValueError):
        return jsonify({"error": "TTL inválido."}), 400

    if seconds < 5:
        return jsonify({"error": "El TTL debe ser de al menos 5 segundos."}), 400

    _CACHE_TTL = timedelta(seconds=seconds)
    _CACHE.clear()
    _persist_cache_settings(seconds)
    _record_cache_event("ttl_update", ttl_seconds=seconds)
    current_app.config["REPORT_CACHE_TTL"] = seconds
    _logger.info("cache-ttl-update ttl=%s", seconds)
    return jsonify({
        "message": "TTL actualizado correctamente.",
        "ttl_seconds": seconds,
    })


@reportes_bp.record_once
def _bootstrap_cache_config(state):
    """Carga la configuración persistida apenas se registra el blueprint."""

    app = state.app
    with app.app_context():
        _load_cache_settings()


def _get_intervalo(default="mes"):
    """Normaliza el parámetro ?interval= y lo valida contra la lista permitida."""

    intervalo = (request.args.get("interval", default) or default).lower()
    if intervalo not in _VALID_INTERVALS:
        return None
    return intervalo


@reportes_bp.route('/graficas', methods=["GET"])
@login_required
@role_required("admin")
def graficas():
    return render_template("graficas.html")


@reportes_bp.route('/data/distribucion_productos')
@login_required
@role_required("admin")
def data_distribucion_productos():
    def _builder():
        productos = (
            db.session.query(Producto.tipo_producto, func.count(Producto.id))
            .group_by(Producto.tipo_producto)
            .order_by(Producto.tipo_producto)
            .all()
        )
        return {
            'tipos': [producto.tipo_producto for producto in productos],
            'cantidades': [producto[1] for producto in productos],
        }

    return _cached_json("distribucion_productos", _builder)


@reportes_bp.route('/data/ventas_totales')
@login_required
@role_required("admin")
def data_ventas_totales():
    intervalo = _get_intervalo()
    if intervalo is None:
        return jsonify({'error': 'Intervalo no válido'}), 400
    cache_key = _make_cache_key("ventas_totales", intervalo=intervalo)

    def _builder():
        ventas_totales = defaultdict(float)
        orden = {}
        etiqueta_periodo = None
        for compra in Compra.query.all():
            clave, label, etiqueta_periodo = _period_key_and_label(compra.fecha, intervalo)
            ventas_totales[label] += float(compra.total or 0)
            orden[label] = clave

        if etiqueta_periodo is None:
            _, _, etiqueta_periodo = _period_key_and_label(datetime.now(timezone.utc), intervalo)

        periodos = [label for label, _ in sorted(orden.items(), key=lambda item: item[1])]
        totales = [ventas_totales[label] for label in periodos]
        return {'periodos': periodos, 'totales': totales, 'period_label': etiqueta_periodo}

    return _cached_json(cache_key, _builder)


@reportes_bp.route('/data/productos_mas_vendidos')
@login_required
@role_required("admin")
def data_productos_mas_vendidos():
    def _builder():
        ventas = (
            db.session.query(Producto.modelo, func.sum(Compra.cantidad).label('cantidad'))
            .join(Producto, Producto.id == Compra.producto_id)
            .group_by(Producto.id)
            .order_by(func.sum(Compra.cantidad).desc())
            .limit(10)
            .all()
        )
        return {
            'productos': [venta[0] for venta in ventas],
            'cantidades': [venta[1] for venta in ventas],
        }

    return _cached_json("productos_mas_vendidos", _builder)


@reportes_bp.route('/data/usuarios_registrados')
@login_required
@role_required("admin")
def data_usuarios_registrados():
    intervalo = _get_intervalo()
    if intervalo is None:
        return jsonify({'error': 'Intervalo no válido'}), 400
    cache_key = _make_cache_key("usuarios_registrados", intervalo=intervalo)

    def _builder():
        totales = defaultdict(int)
        orden = {}
        for usuario in Usuario.query.order_by(Usuario.fecha_registro.asc()).all():
            clave, label, _ = _period_key_and_label(usuario.fecha_registro, intervalo)
            totales[label] += 1
            orden[label] = clave

        periodos = [label for label, _ in sorted(orden.items(), key=lambda item: item[1])]
        conteos = [totales[label] for label in periodos]
        return {'periodos': periodos, 'totales': conteos}

    return _cached_json(cache_key, _builder)


@reportes_bp.route('/data/ingresos_por_usuario')
@login_required
@role_required("admin")
def data_ingresos_por_usuario():
    intervalo = _get_intervalo()
    if intervalo is None:
        return jsonify({'error': 'Intervalo no válido'}), 400
    cache_key = _make_cache_key("ingresos_por_usuario", intervalo=intervalo)

    def _builder():
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
        return {'usuarios': usuarios, 'ingresos': totales}

    return _cached_json(cache_key, _builder)


@reportes_bp.route('/data/compras_por_categoria')
@login_required
@role_required("admin")
def data_compras_por_categoria():
    def _builder():
        compras = db.session.query(
            Producto.tipo_producto,
            func.count(Compra.id).label('total')
        ).join(Compra).group_by(Producto.tipo_producto).all()
        return {
            'categorias': [compra.tipo_producto for compra in compras],
            'compras': [compra.total for compra in compras],
        }

    return _cached_json("compras_por_categoria", _builder)


@reportes_bp.route('/data/productos_menos_vendidos')
@login_required
@role_required("admin")
def data_productos_menos_vendidos():
    def _builder():
        ventas = db.session.query(
            Compra.producto_id,
            func.sum(Compra.cantidad).label('cantidad')
        ).group_by(Compra.producto_id).order_by(func.sum(Compra.cantidad).asc()).limit(10).all()

        return {
            'productos': [db.session.get(Producto, venta.producto_id).modelo for venta in ventas],
            'cantidades': [venta.cantidad for venta in ventas],
        }

    return _cached_json("productos_menos_vendidos", _builder)


@reportes_bp.route("/graficas_cliente", methods=["GET"])
@login_required
@role_required("cliente")
def graficas_cliente():
    return render_template("graficas-cliente.html")


@reportes_bp.route("/data/cliente/compras_tiempo")
@login_required
@role_required("cliente")
def data_cliente_compras_tiempo():
    """Agrega los totales gastados por el cliente segn el intervalo solicitado."""

    intervalo = _get_intervalo()
    if intervalo is None:
        return jsonify({'error': 'Intervalo no vlido'}), 400
    cache_key = _make_cache_key("cliente_compras_tiempo", usuario=current_user.id, intervalo=intervalo)

    def _builder():
        totales = defaultdict(float)
        orden = {}
        etiqueta_periodo = None

        compras = (
            Compra.query.filter_by(usuario_id=current_user.id)
            .order_by(Compra.fecha.asc())
            .all()
        )

        for compra in compras:
            clave, label, etiqueta_periodo = _period_key_and_label(compra.fecha, intervalo)
            totales[label] += float(compra.total or 0)
            orden[label] = clave

        if etiqueta_periodo is None:
            _, _, etiqueta_periodo = _period_key_and_label(datetime.now(timezone.utc), intervalo)

        periodos = [label for label, _ in sorted(orden.items(), key=lambda item: item[1])]
        montos = [totales[label] for label in periodos]
        return {"periodos": periodos, "totales": montos, "period_label": etiqueta_periodo}

    return _cached_json(cache_key, _builder)


@reportes_bp.route("/data/cliente/productos_favoritos")
@login_required
@role_required("cliente")
def data_cliente_productos_favoritos():
    """Top de productos comprados por el cliente actual."""

    cache_key = _make_cache_key("cliente_favoritos", usuario=current_user.id)

    def _builder():
        favoritos = (
            db.session.query(Producto.modelo, func.sum(Compra.cantidad).label("cantidad"))
            .join(Producto, Producto.id == Compra.producto_id)
            .filter(Compra.usuario_id == current_user.id)
            .group_by(Producto.id)
            .order_by(func.sum(Compra.cantidad).desc())
            .limit(5)
            .all()
        )
        return {"productos": [modelo for modelo, _ in favoritos], "cantidades": [cantidad for _, cantidad in favoritos]}

    return _cached_json(cache_key, _builder)


@reportes_bp.route("/data/cliente/estados_pedido")
@login_required
@role_required("cliente")
def data_cliente_estados_pedido():
    """Distribucin de pedidos por estado para el cliente actual."""

    cache_key = _make_cache_key("cliente_estados", usuario=current_user.id)

    def _builder():
        estados = (
            db.session.query(Compra.estado, func.count(Compra.id).label("total"))
            .filter(Compra.usuario_id == current_user.id)
            .group_by(Compra.estado)
            .all()
        )
        return {"estados": [estado for estado, _ in estados], "totales": [total for _, total in estados]}

    return _cached_json(cache_key, _builder)
