"""Funciones compartidas entre blueprints para mantener reglas coherentes.

Se centralizan validaciones y decoradores que antes vivían en `routes.py`
para que cada módulo use la misma lógica sin duplicarla.
"""

from datetime import datetime, timezone
from functools import wraps

from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from markupsafe import escape

from ..db import db
from ..models import ActividadUsuario


def role_required(role):
    """Enforce a single-role access check reused across blueprints.

    Se mantiene aquí para que tanto inventario como reportes compartan
    el mismo comportamiento y los flashes se gestionen de forma homogénea.
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.rol != role:
                flash("Acceso denegado.", "danger")
                # Redirigimos a la portada para evitar endpoints inexistentes.
                return redirect(url_for("auth.root"))
            return f(*args, **kwargs)

        return wrapped

    return decorator


def registrar_actividad(usuario_id, accion, modulo):
    """Persist activity logs with rollback seguro on failure.

    Se conserva el mismo esquema de registro pero aislado para que cualquier
    blueprint pueda auditar acciones sin crear importaciones circulares.
    """

    try:
        nueva_actividad = ActividadUsuario(
            usuario_id=usuario_id,
            accion=accion,
            modulo=modulo,
        )
        db.session.add(nueva_actividad)
        db.session.commit()
    except Exception as exc:  # pragma: no cover - se loguea pero no rompe la UX
        db.session.rollback()
        current_app.logger.error("Error al registrar la actividad: %s", exc)


def _sanitize_csv_value(value):
    """Evita inyecciones CSV (Excel) ante datos controlados por usuario."""

    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return f"'{text}"
    return text


def write_safe_csv_row(writer, values):
    """Escribe una fila CSV sanitizando posibles payloads de fórmulas."""

    writer.writerow([_sanitize_csv_value(val) for val in values])


def _period_key_and_label(moment: datetime, intervalo: str):
    """Agrupa fechas en Python para compatibilidad entre motores SQL.

    Al mantener la lógica en Python evitamos usar funciones específicas de
    SQLite o Postgres y garantizamos ordenamiento estable en pruebas.
    """

    safe_moment = moment or datetime.now(timezone.utc)
    normalized = (intervalo or "mes").lower()

    if normalized == "dia":
        key = (safe_moment.year, safe_moment.month, safe_moment.day)
        return key, f"{safe_moment.year:04d}-{safe_moment.month:02d}-{safe_moment.day:02d}", "Día"
    if normalized == "semana":
        iso = safe_moment.isocalendar()
        key = (iso.year, iso.week)
        return key, f"{iso.year}-W{iso.week:02d}", "Semana"
    if normalized == "trimestre":
        trimestre = (safe_moment.month - 1) // 3 + 1
        key = (safe_moment.year, trimestre)
        return key, f"{safe_moment.year}-T{trimestre}", "Trimestre"
    if normalized == "anio":
        key = (safe_moment.year,)
        return key, f"{safe_moment.year}", "Año"

    key = (safe_moment.year, safe_moment.month)
    return key, f"{safe_moment.year:04d}-{safe_moment.month:02d}", "Mes"


def _extract_productos(source):
    """Normaliza valores recibidos desde WTForms o MultiDict."""

    if hasattr(source, "getlist"):
        return source.getlist("productos")

    raw = source.get("productos")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(item) for item in raw]
    return [raw]


def validar_datos_proveedor(form):
    """Valida campos mínimos y convierte valores numéricos de proveedores.

    Se concentra en un helper para que tanto altas como ediciones de
    proveedores reaprovechen la misma validación previa al commit.
    """

    required_fields = ["nombre", "telefono", "direccion", "email", "cif", "tasa_de_descuento", "iva"]
    for field in required_fields:
        value = form.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, f"El campo '{field}' es obligatorio."

    try:
        tasa_de_descuento = float(form.get("tasa_de_descuento"))
        iva = float(form.get("iva"))
    except (TypeError, ValueError):
        return False, "Los campos 'Tasa de descuento' e 'IVA' deben ser números válidos."

    productos = [item for item in _extract_productos(form) if item]
    productos_str = ", ".join(productos) if productos else "No especificado"

    datos = {
        "nombre": escape(form.get("nombre")),
        "telefono": escape(form.get("telefono")),
        "direccion": escape(form.get("direccion")),
        "email": escape(form.get("email")),
        "cif": escape(form.get("cif")),
        "tasa_de_descuento": tasa_de_descuento,
        "iva": iva,
        "tipo_producto": productos_str,
    }
    return True, datos
