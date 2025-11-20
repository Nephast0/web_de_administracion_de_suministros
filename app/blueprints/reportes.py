"""Blueprint de reportes y endpoints de datos agregados."""

import csv
import json
import logging
import os
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
from flask import Blueprint, Response, abort, current_app, jsonify, render_template, request
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
_CACHE_HISTORY: deque[dict] = deque(maxlen=200)
_DEFAULT_CACHE_TTL = int(os.getenv("REPORT_CACHE_TTL", "60"))
_CACHE_TTL = timedelta(seconds=_DEFAULT_CACHE_TTL)
_INSTANCE_DIR = Path(__file__).resolve().parents[2] / "instance"
_CACHE_FILE_FALLBACK = _INSTANCE_DIR / "report_cache.json"
_CACHE_HISTORY_FILE_FALLBACK = _INSTANCE_DIR / "cache_history.json"
_CACHE_HISTORY_MAX_BYTES = int(os.getenv("REPORT_CACHE_HISTORY_MAX_BYTES", "524288"))
_CACHE_HISTORY_ARCHIVE_DIR = _INSTANCE_DIR / "cache_history_archive"


def _make_cache_key(prefix: str, **params) -> str:
    """Genera una clave estable para almacenar respuestas JSON en memoria."""

    serialized = "|".join(f"{key}:{params[key]}" for key in sorted(params))
    return f"{prefix}|{serialized}"


def _get_cache_file() -> Path:
    try:
        override = current_app.config.get("REPORT_CACHE_FILE")
    except RuntimeError:
        override = None
    override = override or os.getenv("REPORT_CACHE_FILE")
    if override:
        return Path(override)
    return _CACHE_FILE_FALLBACK


def _get_cache_history_file() -> Path:
    try:
        override = current_app.config.get("REPORT_CACHE_HISTORY_FILE")
    except RuntimeError:
        override = None
    override = override or os.getenv("REPORT_CACHE_HISTORY_FILE")
    if override:
        return Path(override)
    return _CACHE_HISTORY_FILE_FALLBACK


def _get_cache_history_archive_dir() -> Path:
    try:
        override = current_app.config.get("REPORT_CACHE_HISTORY_ARCHIVE_DIR")
    except RuntimeError:
        override = None
    override = override or os.getenv("REPORT_CACHE_HISTORY_ARCHIVE_DIR")
    if override:
        return Path(override)
    return _CACHE_HISTORY_ARCHIVE_DIR


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


def _load_cache_history():
    path = _get_cache_history_file()
    if not path.exists():
        return
    try:
        events = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _logger.warning("No se pudo cargar el historial de caché: %s", exc)
        return
    _CACHE_HISTORY.clear()
    for event in events[-_CACHE_HISTORY.maxlen:]:
        _CACHE_HISTORY.append(event)


def _persist_cache_history():
    path = _get_cache_history_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(list(_CACHE_HISTORY), ensure_ascii=False, indent=2)
    path.write_text(payload, encoding="utf-8")
    _rotate_cache_history_if_needed()


def _rotate_cache_history_if_needed():
    path = _get_cache_history_file()
    try:
        max_bytes = int(current_app.config.get("REPORT_CACHE_HISTORY_MAX_BYTES", _CACHE_HISTORY_MAX_BYTES))
    except (RuntimeError, TypeError, ValueError):
        max_bytes = _CACHE_HISTORY_MAX_BYTES
    if not path.exists() or path.stat().st_size <= max_bytes:
        return
    archive_dir = _get_cache_history_archive_dir()
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    archive_path = archive_dir / f"cache_history_{timestamp}.json"
    path.replace(archive_path)
    # Reescribimos el archivo principal con los eventos actuales en memoria.
    path.write_text(json.dumps(list(_CACHE_HISTORY), ensure_ascii=False, indent=2), encoding="utf-8")


def _collect_history_events(include_archives: bool = False):
    events = []
    path = _get_cache_history_file()
    if path.exists():
        try:
            events.extend(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            _logger.warning("No se pudo leer el historial base, se usará sólo la memoria.")
    archive_dir = _get_cache_history_archive_dir()
    if include_archives and archive_dir.exists():
        archive_files = sorted(archive_dir.glob("cache_history_*.json"))
        for file_path in archive_files:
            try:
                events.extend(json.loads(file_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                _logger.warning("No se pudo leer el archivo de historial %s", file_path)
    return events or list(_CACHE_HISTORY)


def _load_cache_history():
    path = _get_cache_history_file()
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _logger.warning("No se pudo leer el historial persistido de caché.")
        return
    _CACHE_HISTORY.clear()
    for event in reversed(data[-_CACHE_HISTORY.maxlen:]):
        _CACHE_HISTORY.appendleft(event)


def _persist_cache_history():
    path = _get_cache_history_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(_CACHE_HISTORY), indent=2), encoding="utf-8")


def _record_cache_event(event_type: str, **extra):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **extra,
    }
    _CACHE_HISTORY.appendleft(event)
    try:
        _persist_cache_history()
    except OSError as exc:
        _logger.warning("No se pudo persistir el histórico de caché: %s", exc)


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


@reportes_bp.route("/data/cache_history/export")
@login_required
@role_required("admin")
def cache_history_export():
    """Permite descargar el historial persistente en un archivo JSON."""

    include_archives = request.args.get("include_archives", "0").lower() in {"1", "true", "yes", "y"}
    events = _collect_history_events(include_archives)
    payload = json.dumps({"events": events}, ensure_ascii=False, indent=2)
    response = Response(payload, mimetype="application/json")
    response.headers["Content-Disposition"] = "attachment; filename=cache_history.json"
    return response


@reportes_bp.route("/data/chart_export/<string:chart_name>")
@login_required
@role_required("admin")
def chart_export(chart_name):
    """Genera un CSV con los datos de una gráfica."""

    chart = _CHART_EXPORTERS.get(chart_name)
    if not chart:
        abort(404)

    params = {}
    if chart.get("requires_interval"):
        intervalo = _get_intervalo()
        if intervalo is None:
            return jsonify({'error': 'Intervalo no válido'}), 400
        params["interval"] = intervalo
    else:
        params["interval"] = request.args.get("interval")

    dataset = chart["builder"](params)
    rows = chart["rows"](dataset)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(chart["headers"])
    for row in rows:
        writer.writerow(row)

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={chart_name}.csv"
    return response


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
        _load_cache_history()


def _get_intervalo(default="mes"):
    """Normaliza el parámetro ?interval= y lo valida contra la lista permitida."""

    intervalo = (request.args.get("interval", default) or default).lower()
    if intervalo not in _VALID_INTERVALS:
        return None
    return intervalo


def _dataset_distribucion_productos():
    productos = (
        db.session.query(Producto.tipo_producto, func.count(Producto.id))
        .group_by(Producto.tipo_producto)
        .order_by(Producto.tipo_producto)
        .all()
    )
    return {
        "tipos": [producto.tipo_producto for producto in productos],
        "cantidades": [producto[1] for producto in productos],
    }


def _dataset_ventas_totales(intervalo: str):
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
    return {"periodos": periodos, "totales": totales, "period_label": etiqueta_periodo}


def _dataset_productos_mas_vendidos(limit=10):
    ventas = (
        db.session.query(Producto.modelo, func.sum(Compra.cantidad).label("cantidad"))
        .join(Producto, Producto.id == Compra.producto_id)
        .group_by(Producto.id)
        .order_by(func.sum(Compra.cantidad).desc())
        .limit(limit)
        .all()
    )
    return {"productos": [venta[0] for venta in ventas], "cantidades": [venta[1] for venta in ventas]}


def _dataset_usuarios_registrados(intervalo: str):
    totales = defaultdict(int)
    orden = {}
    for usuario in Usuario.query.order_by(Usuario.fecha_registro.asc()).all():
        clave, label, _ = _period_key_and_label(usuario.fecha_registro, intervalo)
        totales[label] += 1
        orden[label] = clave

    periodos = [label for label, _ in sorted(orden.items(), key=lambda item: item[1])]
    conteos = [totales[label] for label in periodos]
    return {"periodos": periodos, "totales": conteos}


def _dataset_ingresos_por_usuario(intervalo: str):
    ingresos = defaultdict(float)
    orden = {}

    compras = (
        db.session.query(Compra.usuario_id, Compra.fecha, Compra.total)
        .join(Usuario, Usuario.id == Compra.usuario_id)
        .order_by(Compra.fecha.asc())
        .all()
    )

    for compra in compras:
        clave_periodo, etiqueta, _ = _period_key_and_label(compra.fecha, intervalo)
        clave = (compra.usuario_id, etiqueta)
        ingresos[clave] += float(compra.total or 0)
        orden[clave] = clave_periodo

    ordered_keys = [key for key, _ in sorted(orden.items(), key=lambda item: item[1])]
    usuarios = [f"{usuario} ({periodo})" for (usuario, periodo) in ordered_keys]
    totales = [ingresos[(usuario, periodo)] for (usuario, periodo) in ordered_keys]
    return {"usuarios": usuarios, "ingresos": totales}


def _dataset_productos_menos_vendidos(limit=10):
    ventas = (
        db.session.query(Compra.producto_id, func.sum(Compra.cantidad).label("cantidad"))
        .group_by(Compra.producto_id)
        .order_by(func.sum(Compra.cantidad).asc())
        .limit(limit)
        .all()
    )

    return {
        "productos": [db.session.get(Producto, venta.producto_id).modelo for venta in ventas],
        "cantidades": [venta.cantidad for venta in ventas],
    }


def _dataset_compras_por_categoria():
    compras = (
        db.session.query(Producto.tipo_producto, func.count(Compra.id).label("total"))
        .join(Compra)
        .group_by(Producto.tipo_producto)
        .all()
    )
    return {"categorias": [compra.tipo_producto for compra in compras], "compras": [compra.total for compra in compras]}


_CHART_EXPORTERS = {
    "distribucion_productos": {
        "requires_interval": False,
        "builder": lambda params: _dataset_distribucion_productos(),
        "headers": ("tipo_producto", "cantidad"),
        "rows": lambda data: zip(data["tipos"], data["cantidades"]),
    },
    "ventas_totales": {
        "requires_interval": True,
        "builder": lambda params: _dataset_ventas_totales(params["interval"]),
        "headers": ("periodo", "total"),
        "rows": lambda data: zip(data["periodos"], data["totales"]),
    },
    "productos_mas_vendidos": {
        "requires_interval": False,
        "builder": lambda params: _dataset_productos_mas_vendidos(),
        "headers": ("producto", "cantidad"),
        "rows": lambda data: zip(data["productos"], data["cantidades"]),
    },
    "usuarios_registrados": {
        "requires_interval": True,
        "builder": lambda params: _dataset_usuarios_registrados(params["interval"]),
        "headers": ("periodo", "usuarios"),
        "rows": lambda data: zip(data["periodos"], data["totales"]),
    },
    "ingresos_por_usuario": {
        "requires_interval": True,
        "builder": lambda params: _dataset_ingresos_por_usuario(params["interval"]),
        "headers": ("usuario_periodo", "ingresos"),
        "rows": lambda data: zip(data["usuarios"], data["ingresos"]),
    },
}


@reportes_bp.route('/graficas', methods=["GET"])
@login_required
@role_required("admin")
def graficas():
    return render_template("graficas.html")


@reportes_bp.route('/data/distribucion_productos')
@login_required
@role_required("admin")
def data_distribucion_productos():
    return _cached_json("distribucion_productos", _dataset_distribucion_productos)


@reportes_bp.route('/data/ventas_totales')
@login_required
@role_required("admin")
def data_ventas_totales():
    intervalo = _get_intervalo()
    if intervalo is None:
        return jsonify({'error': 'Intervalo no válido'}), 400
    cache_key = _make_cache_key("ventas_totales", intervalo=intervalo)

    return _cached_json(cache_key, lambda: _dataset_ventas_totales(intervalo))


@reportes_bp.route('/data/productos_mas_vendidos')
@login_required
@role_required("admin")
def data_productos_mas_vendidos():
    return _cached_json("productos_mas_vendidos", _dataset_productos_mas_vendidos)


@reportes_bp.route('/data/usuarios_registrados')
@login_required
@role_required("admin")
def data_usuarios_registrados():
    intervalo = _get_intervalo()
    if intervalo is None:
        return jsonify({'error': 'Intervalo no válido'}), 400
    cache_key = _make_cache_key("usuarios_registrados", intervalo=intervalo)

    return _cached_json(cache_key, lambda: _dataset_usuarios_registrados(intervalo))


@reportes_bp.route('/data/ingresos_por_usuario')
@login_required
@role_required("admin")
def data_ingresos_por_usuario():
    intervalo = _get_intervalo()
    if intervalo is None:
        return jsonify({'error': 'Intervalo no válido'}), 400
    cache_key = _make_cache_key("ingresos_por_usuario", intervalo=intervalo)

    return _cached_json(cache_key, lambda: _dataset_ingresos_por_usuario(intervalo))


@reportes_bp.route('/data/compras_por_categoria')
@login_required
@role_required("admin")
def data_compras_por_categoria():
    return _cached_json("compras_por_categoria", _dataset_compras_por_categoria)


@reportes_bp.route('/data/productos_menos_vendidos')
@login_required
@role_required("admin")
def data_productos_menos_vendidos():
    return _cached_json("productos_menos_vendidos", _dataset_productos_menos_vendidos)


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
