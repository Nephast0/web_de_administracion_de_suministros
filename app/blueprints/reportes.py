"""Blueprint de reportes y endpoints de datos agregados."""

import csv
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
from flask import Blueprint, Response, abort, current_app, jsonify, render_template, request, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, case

from ..db import db
from ..models import Compra, Producto, Usuario, CacheEvent, Cuenta, Apunte, Asiento
from .helpers import _period_key_and_label, role_required


reportes_bp = Blueprint("reportes", __name__)
_logger = logging.getLogger(__name__)
_VALID_INTERVALS = {"dia", "semana", "mes", "trimestre", "anio"}
_CACHE: dict[str, dict] = {}
_CACHE_STATS = {"hits": 0, "misses": 0}
_DEFAULT_CACHE_TTL = int(os.getenv("REPORT_CACHE_TTL", "60"))
_CACHE_TTL = timedelta(seconds=_DEFAULT_CACHE_TTL)
_INSTANCE_DIR = Path(__file__).resolve().parents[2] / "instance"
_CACHE_FILE_FALLBACK = _INSTANCE_DIR / "report_cache.json"
_HISTORY_FILE_FALLBACK = _INSTANCE_DIR / "cache_history.json"
_HISTORY_ARCHIVE_DIR_FALLBACK = _INSTANCE_DIR / "cache_history_archive"
_DEFAULT_HISTORY_MAX_BYTES = int(os.getenv("REPORT_CACHE_HISTORY_MAX_BYTES", "524288"))
_DEFAULT_HISTORY_MAX_RECORDS = int(os.getenv("REPORT_CACHE_HISTORY_MAX_RECORDS", "2000"))
_DEFAULT_HISTORY_MAX_DAYS = int(os.getenv("REPORT_CACHE_HISTORY_MAX_DAYS", "90"))
_DEFAULT_HISTORY_MAX_BYTES = int(os.getenv("REPORT_CACHE_HISTORY_MAX_BYTES", "524288"))
_DEFAULT_HISTORY_MAX_RECORDS = int(os.getenv("REPORT_CACHE_HISTORY_MAX_RECORDS", "2000"))
_HISTORY_FILE_FALLBACK = _INSTANCE_DIR / "cache_history.json"
_HISTORY_ARCHIVE_DIR_FALLBACK = _INSTANCE_DIR / "cache_history_archive"
_DEFAULT_HISTORY_MAX_BYTES = int(os.getenv("REPORT_CACHE_HISTORY_MAX_BYTES", "524288"))


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
    return Path(override) if override else _HISTORY_FILE_FALLBACK


def _get_cache_history_archive_dir() -> Path:
    try:
        override = current_app.config.get("REPORT_CACHE_HISTORY_ARCHIVE_DIR")
    except RuntimeError:
        override = None
    override = override or os.getenv("REPORT_CACHE_HISTORY_ARCHIVE_DIR")
    return Path(override) if override else _HISTORY_ARCHIVE_DIR_FALLBACK


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


def _load_history_events(include_archives: bool = False) -> list[dict]:
    """Carga eventos de historial desde archivos activos y archivados."""
    events: list[dict] = []
    path = _get_cache_history_file()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                events.extend(payload.get("events", []))
            elif isinstance(payload, list):
                events.extend(payload)
        except (json.JSONDecodeError, OSError, ValueError):
            _logger.warning("Historial de cache corrupto, se reiniciará")

    if include_archives:
        archive_dir = _get_cache_history_archive_dir()
        if archive_dir.exists():
            for archive_file in sorted(archive_dir.glob("cache_history_*.json")):
                try:
                    payload = json.loads(archive_file.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        events.extend(payload.get("events", []))
                    elif isinstance(payload, list):
                        events.extend(payload)
                except (json.JSONDecodeError, OSError, ValueError):
                    _logger.warning("Archivo de historial en archivo dañado: %s", archive_file)
    return events



def _persist_history_events(events: list[dict], path: Path | None = None):
    target = path or _get_cache_history_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"events": events}, ensure_ascii=False, indent=2), encoding="utf-8")


def _rotate_cache_history_if_needed():
    path = _get_cache_history_file()
    if not path.exists():
        return
    try:
        max_bytes = int(
            current_app.config.get(
                "REPORT_CACHE_HISTORY_MAX_BYTES",
                os.getenv("REPORT_CACHE_HISTORY_MAX_BYTES", _DEFAULT_HISTORY_MAX_BYTES),
            )
        )
    except Exception:
        max_bytes = _DEFAULT_HISTORY_MAX_BYTES

    if max_bytes and path.stat().st_size > max_bytes:
        archive_dir = _get_cache_history_archive_dir()
        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        archive_path = archive_dir / f"cache_history_{timestamp}.json"
        path.replace(archive_path)
        _persist_history_events([])


def _append_history_event(event: dict):
    path = _get_cache_history_file()
    try:
        _rotate_cache_history_if_needed()
        events: list[dict] = []
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    events = payload.get("events", [])
                elif isinstance(payload, list):
                    events = payload
            except (json.JSONDecodeError, OSError, ValueError):
                events = []
        events.append(event)
        _persist_history_events(events, path)
    except Exception as exc:  # pragma: no cover - los fallos de logging no deben romper el flujo
        _logger.warning("No se pudo registrar historial de cache en archivo: %s", exc)




def _trim_cache_events(max_records: int = _DEFAULT_HISTORY_MAX_RECORDS):
    """Limita el tamaño de CacheEvent para evitar crecimiento ilimitado."""
    try:
        total = CacheEvent.query.count()
        if max_records and total > max_records:
            overflow = total - max_records
            (
                CacheEvent.query.order_by(CacheEvent.timestamp.asc())
                .limit(overflow)
                .delete(synchronize_session=False)
            )
            db.session.commit()
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        _logger.warning("No se pudo recortar CacheEvent: %s", exc)


def _purge_cache_events_older_than(days: int = _DEFAULT_HISTORY_MAX_DAYS):
    """Elimina eventos muy antiguos para retención temporal."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        CacheEvent.query.filter(CacheEvent.timestamp < cutoff).delete(synchronize_session=False)
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        _logger.warning("No se pudieron purgar eventos antiguos: %s", exc)


def _persist_cache_settings(seconds: int):
    path = _get_cache_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ttl_seconds": seconds, "updated_at": datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _record_cache_event(event_type: str, **extra):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "details": extra,
    }
    try:
        details = json.dumps(extra, ensure_ascii=False)
        event_row = CacheEvent(event_type=event_type, details=details)
        db.session.add(event_row)
        db.session.commit()
        _trim_cache_events()
        _purge_cache_events_older_than()
        _append_history_event(event)
    except Exception as exc:
        db.session.rollback()
        _logger.warning("No se pudo persistir el evento de caché: %s", exc)
        _append_history_event(event)



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



@reportes_bp.route("")
@reportes_bp.route("/")
@login_required
def index():
    if current_user.role == 'admin':
        return redirect(url_for('reportes.graficas'))
    elif current_user.role == 'cliente':
        return redirect(url_for('reportes.graficas_cliente'))
    return redirect(url_for('main.index'))


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
    """Devuelve los eventos recientes registrados en la caché con paginación."""
    try:
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("page_size", 100)), 500)
    except (TypeError, ValueError):
        return jsonify({"error": "Parámetros de paginación inválidos"}), 400

    events = _load_history_events()
    events_sorted = sorted(events, key=lambda e: e.get("timestamp", ""), reverse=True)
    total = len(events_sorted)
    start = max(page - 1, 0) * per_page
    end = start + per_page
    page_events = events_sorted[start:end]

    return jsonify({
        "events": page_events,
        "pagination": {
            "page": page,
            "page_size": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page if per_page else 0,
        },
    })


@reportes_bp.route("/data/cache_history/export")
@login_required
@role_required("admin")
def cache_history_export():
    """Permite descargar el historial persistente en un archivo JSON."""
    include_archives = str(request.args.get("include_archives", "0")).lower() in {"1", "true", "yes"}
    events = _load_history_events(include_archives=include_archives)
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

@reportes_bp.route("/data/chart_export_cliente/<string:chart_name>")
@login_required
@role_required("cliente")
def chart_export_cliente(chart_name):
    """Genera un CSV con los datos de una gráfica de cliente."""
    exporters = {
        "cliente_compras_tiempo": {
            "builder": lambda: _dataset_cliente_compras_tiempo_builder(_get_intervalo()),
            "headers": ("periodo", "total"),
            "rows": lambda data: zip(data["periodos"], data["totales"])
        },
        "cliente_productos_favoritos": {
            "builder": lambda: _dataset_cliente_productos_favoritos_builder(),
            "headers": ("producto", "cantidad"),
            "rows": lambda data: zip(data["productos"], data["cantidades"])
        },
        "cliente_estados_pedido": {
            "builder": lambda: _dataset_cliente_estados_pedido_builder(),
            "headers": ("estado", "total"),
            "rows": lambda data: zip(data["estados"], data["totales"])
        }
    }
    
    chart = exporters.get(chart_name)
    if not chart:
        abort(404)
        
    dataset = chart["builder"]()
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


def _dataset_ingresos_gastos(intervalo: str):
    """Calcula Ingresos (Grupo 7) vs Gastos (Grupo 6) en el tiempo."""
    ingresos = defaultdict(float)
    gastos = defaultdict(float)
    orden = {}
    etiqueta_periodo = None

    # Consulta de apuntes de cuentas de grupo 6 y 7
    apuntes = (
        db.session.query(Apunte, Cuenta.codigo, Asiento.fecha)
        .join(Cuenta, Apunte.cuenta_id == Cuenta.id)
        .join(Asiento, Apunte.asiento_id == Asiento.id)
        .filter(
            (Cuenta.codigo.like('6%')) | (Cuenta.codigo.like('7%'))
        )
        .order_by(Asiento.fecha.asc())
        .all()
    )

    for apunte, codigo, fecha in apuntes:
        clave, label, etiqueta_periodo = _period_key_and_label(fecha, intervalo)
        orden[label] = clave
        
        saldo = float(apunte.haber - apunte.debe)
        
        if codigo.startswith('7'): # Ingreso
             # En contabilidad, ingresos (Haber) aumentan. Haber - Debe > 0
             # Si es devolucion (Debe), resta.
             ingresos[label] += saldo
        elif codigo.startswith('6'): # Gasto
             # Gastos (Debe) aumentan. Haber - Debe < 0.
             # Queremos mostrar gastos como positivo en la gráfica comparativa, o negativo?
             # Normalmente se comparan barras positivas.
             # Gasto neto = Debe - Haber.
             gastos[label] += float(apunte.debe - apunte.haber)

    if etiqueta_periodo is None:
        _, _, etiqueta_periodo = _period_key_and_label(datetime.now(timezone.utc), intervalo)

    periodos = [label for label, _ in sorted(orden.items(), key=lambda item: item[1])]
    data_ingresos = [ingresos[label] for label in periodos]
    data_gastos = [gastos[label] for label in periodos]

    return {
        "periodos": periodos, 
        "ingresos": data_ingresos, 
        "gastos": data_gastos, 
        "period_label": etiqueta_periodo
    }


# --- Builders para Cliente ---

def _dataset_cliente_compras_tiempo_builder(intervalo):
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

def _dataset_cliente_productos_favoritos_builder():
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

def _dataset_cliente_estados_pedido_builder():
    estados = (
        db.session.query(Compra.estado, func.count(Compra.id).label("total"))
        .filter(Compra.usuario_id == current_user.id)
        .group_by(Compra.estado)
        .all()
    )
    return {"estados": [estado for estado, _ in estados], "totales": [total for _, total in estados]}


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
    "ingresos_gastos": {
        "requires_interval": True,
        "builder": lambda params: _dataset_ingresos_gastos(params["interval"]),
        "headers": ("periodo", "ingresos", "gastos"),
        "rows": lambda data: zip(data["periodos"], data["ingresos"], data["gastos"]),
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


@reportes_bp.route('/data/ingresos_gastos')
@login_required
@role_required("admin")
def data_ingresos_gastos():
    intervalo = _get_intervalo()
    if intervalo is None:
        return jsonify({'error': 'Intervalo no válido'}), 400
    cache_key = _make_cache_key("ingresos_gastos", intervalo=intervalo)

    return _cached_json(cache_key, lambda: _dataset_ingresos_gastos(intervalo))


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

    return _cached_json(cache_key, lambda: _dataset_cliente_compras_tiempo_builder(intervalo))


@reportes_bp.route("/data/cliente/productos_favoritos")
@login_required
@role_required("cliente")
def data_cliente_productos_favoritos():
    """Top de productos comprados por el cliente actual."""
    cache_key = _make_cache_key("cliente_favoritos", usuario=current_user.id)
    return _cached_json(cache_key, _dataset_cliente_productos_favoritos_builder)


@reportes_bp.route("/data/cliente/estados_pedido")
@login_required
@role_required("cliente")
def data_cliente_estados_pedido():
    """Distribucin de pedidos por estado para el cliente actual."""
    cache_key = _make_cache_key("cliente_estados", usuario=current_user.id)
    return _cached_json(cache_key, _dataset_cliente_estados_pedido_builder)
