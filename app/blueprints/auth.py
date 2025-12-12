"""Blueprint de autenticación y administración de usuarios.

Agrupa las rutas de login/registro y acciones de administración para
reducir el monolito previo y documentar por qué se ajusta cada flujo.
"""

import csv
import io
import time
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    Response,
    current_app as app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ..db import db
from ..extensions import login_manager
from ..forms import Formulario_de_registro, Login_form
from ..models import ActividadUsuario, Compra, Usuario
from .helpers import registrar_actividad, role_required, write_safe_csv_row


auth_bp = Blueprint("auth", __name__)
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_WINDOW_SECONDS = 600
_LOGIN_MAX_ATTEMPTS = 5


def _is_rate_limited():
    """Limitador simple por IP para proteger el login."""

    if app.config.get("TESTING"):
        return False
    ip = request.remote_addr or "unknown"
    now = time.time()
    attempts = [ts for ts in _LOGIN_ATTEMPTS.get(ip, []) if now - ts < _LOGIN_WINDOW_SECONDS]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        return True
    attempts.append(now)
    _LOGIN_ATTEMPTS[ip] = attempts
    return False


def _reset_rate_limit():
    ip = request.remote_addr or "unknown"
    _LOGIN_ATTEMPTS.pop(ip, None)


@login_manager.user_loader
def cargar_usuario(usuario_id):
    """Obtiene el usuario por ID usando SQLAlchemy 2.x (db.session.get)."""

    return db.session.get(Usuario, str(usuario_id))


@auth_bp.route("/", methods=["GET"])
def root():
    form = Login_form()
    return render_template("index.html", form=form)


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    form = Formulario_de_registro()

    # Verifica si el formulario se envió correctamente
    app.logger.debug("Método de solicitud: %s", request.method)
    if request.method == "POST":
        app.logger.debug("Datos enviados en el formulario: %s", request.form)

    if form.validate_on_submit():
        app.logger.debug("El formulario pasó las validaciones.")

        # Validación previa para evitar IntegrityError y guiar al usuario.
        usuario_existente = Usuario.query.filter_by(usuario=form.usuario.data).first()
        if usuario_existente:
            flash("El nombre de usuario ya está registrado.", "warning")
            return render_template("registro.html", form=form)

        try:
            nuevo_usuario = Usuario(
                nombre=form.nombre.data,
                usuario=form.usuario.data,
                direccion=form.direccion.data,
                contrasenya=form.contrasenya.data,
                rol="cliente",
            )

            app.logger.info("Nuevo usuario creado: %s", nuevo_usuario.usuario)

            db.session.add(nuevo_usuario)
            db.session.commit()
            app.logger.debug("Usuario guardado en la base de datos.")

            registrar_actividad(
                usuario_id=nuevo_usuario.id,
                accion=f"Registró un nuevo usuario: {nuevo_usuario.usuario}",
                modulo="Registro de Usuario",
            )

            flash("¡Tu cuenta ha sido creada con éxito! Ahora puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login", usuario=nuevo_usuario.usuario))

        except Exception:
            app.logger.exception("Error al intentar guardar el usuario en la base de datos")
            db.session.rollback()
            flash("Ocurrió un error al registrar tu usuario.", "danger")

    else:
        app.logger.debug("Errores en la validación del formulario: %s", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {field}: {error}", "warning")

    return render_template("registro.html", form=form)


@auth_bp.route("/login", methods=["POST", "GET"])
def login():
    form = Login_form()
    
    # Pre-fill username if passed from registration
    if request.method == 'GET' and not form.usuario.data:
        usuario_arg = request.args.get('usuario')
        if usuario_arg:
            form.usuario.data = usuario_arg
    app.logger.debug("Datos recibidos del formulario: %s", {**form.data, "contrasenya": "[omitted]"})

    if request.method == "POST" and _is_rate_limited():
        flash("Demasiados intentos de inicio de sesión. Intenta de nuevo en unos minutos.", "danger")
        return render_template("index.html", form=form), 429

    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(usuario=form.usuario.data).first()

        # Validamos la existencia antes de acceder a atributos para evitar AttributeError.
        if not usuario:
            flash("Usuario o contraseña incorrectos.", "danger")
            return render_template("index.html", form=form)

        if usuario.check_contrasenya(form.contrasenya.data):
            session.clear()  # Evita fijación de sesión previa al login.
            login_user(usuario)
            _reset_rate_limit()
            flash(f"¡Bienvenido, {usuario.usuario}!", "success")

            # Derivamos según rol; se podría extender con más roles en el futuro.
            if usuario.rol == "admin":
                return redirect(url_for("inventario.menu_principal"))
            if usuario.rol == "cliente":
                return redirect(url_for("inventario.menu_cliente"))

            flash("Tu cuenta no tiene un rol asignado correctamente.", "warning")
            logout_user()
        else:
            flash("Usuario o contraseña incorrectos.", "danger")

    else:
        app.logger.debug("Errores en la validación del formulario: %s", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {field}: {error}", "warning")

    return render_template("index.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Has cerrado la sesión  correctamente.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/actividades", methods=["GET", "POST"])
@login_required
@role_required("admin")
def actividades():
    # Capturar mensajes de éxito o error desde la URL
    mensaje_exito = request.args.get("flash_success")
    mensaje_error = request.args.get("flash_error")
    def _safe_positive_int(raw, default):
        try:
            return max(int(raw), 1)
        except (TypeError, ValueError):
            return default

    page_act = _safe_positive_int(request.args.get("page_act", 1), 1)
    page_user = _safe_positive_int(request.args.get("page_user", 1), 1)
    page_comp = _safe_positive_int(request.args.get("page_comp", 1), 1)

    try:
        per_page = min(int(request.args.get("page_size", 20)), 50)
    except (TypeError, ValueError):
        per_page = 20

    if mensaje_exito:
        flash(mensaje_exito, "success")
    if mensaje_error:
        flash(mensaje_error, "danger")

    filtro_usuario = (request.args.get("f_usuario") or "").strip()
    filtro_modulo = (request.args.get("f_modulo") or "").strip()
    fecha_inicio_raw = request.args.get("f_desde")
    fecha_fin_raw = request.args.get("f_hasta")
    fecha_inicio = datetime.strptime(fecha_inicio_raw, "%Y-%m-%d") if fecha_inicio_raw else None
    fecha_fin = datetime.strptime(fecha_fin_raw, "%Y-%m-%d") if fecha_fin_raw else None
    if fecha_fin:
        fecha_fin = fecha_fin + timedelta(days=1)

    act_query = ActividadUsuario.query.join(Usuario)
    if filtro_usuario:
        like = f"%{filtro_usuario}%"
        act_query = act_query.filter(Usuario.usuario.ilike(like))
    if filtro_modulo:
        act_query = act_query.filter(ActividadUsuario.modulo.ilike(f"%{filtro_modulo}%"))
    if fecha_inicio:
        act_query = act_query.filter(ActividadUsuario.fecha >= fecha_inicio)
    if fecha_fin:
        act_query = act_query.filter(ActividadUsuario.fecha < fecha_fin)
    actividades_pag = act_query.order_by(ActividadUsuario.fecha.desc()).paginate(page=page_act, per_page=per_page, error_out=False)

    filtro_rol = (request.args.get("f_rol") or "").strip()
    filtro_busqueda = (request.args.get("f_q") or "").strip()
    user_query = Usuario.query
    if filtro_rol:
        user_query = user_query.filter(Usuario.rol == filtro_rol)
    if filtro_busqueda:
        like_u = f"%{filtro_busqueda}%"
        user_query = user_query.filter(Usuario.usuario.ilike(like_u) | Usuario.nombre.ilike(like_u))
    usuarios_pag = user_query.order_by(Usuario.fecha_registro.desc()).paginate(page=page_user, per_page=per_page, error_out=False)

    filtro_estado = (request.args.get("c_estado") or "").strip()
    filtro_fecha_desde = request.args.get("c_desde")
    filtro_fecha_hasta = request.args.get("c_hasta")
    fecha_c_desde = datetime.strptime(filtro_fecha_desde, "%Y-%m-%d") if filtro_fecha_desde else None
    fecha_c_hasta = datetime.strptime(filtro_fecha_hasta, "%Y-%m-%d") if filtro_fecha_hasta else None
    if fecha_c_hasta:
        fecha_c_hasta = fecha_c_hasta + timedelta(days=1)

    compras_query = Compra.query
    if filtro_estado:
        compras_query = compras_query.filter(Compra.estado == filtro_estado)
    if fecha_c_desde:
        compras_query = compras_query.filter(Compra.fecha >= fecha_c_desde)
    if fecha_c_hasta:
        compras_query = compras_query.filter(Compra.fecha < fecha_c_hasta)
    compras_pag = compras_query.order_by(Compra.fecha.desc()).paginate(page=page_comp, per_page=per_page, error_out=False)

    return render_template(
        "menu-admin.html",
        actividades=actividades_pag.items,
        usuarios=usuarios_pag.items,
        compras=compras_pag.items,
        pag_actividades=actividades_pag,
        pag_usuarios=usuarios_pag,
        pag_compras=compras_pag,
        filtros={
            "f_usuario": filtro_usuario,
            "f_modulo": filtro_modulo,
            "f_desde": fecha_inicio_raw or "",
            "f_hasta": fecha_fin_raw or "",
            "f_rol": filtro_rol,
            "f_q": filtro_busqueda,
            "c_estado": filtro_estado,
            "c_desde": filtro_fecha_desde or "",
            "c_hasta": filtro_fecha_hasta or "",
        },
    )


@auth_bp.route("/compras/export", methods=["GET"])
@login_required
@role_required("admin")
def exportar_compras_admin():
    """Exporta las compras del panel admin con filtros aplicados."""

    filtro_estado = (request.args.get("c_estado") or request.args.get("estado") or "").strip()
    filtro_fecha_desde = request.args.get("c_desde") or request.args.get("desde")
    filtro_fecha_hasta = request.args.get("c_hasta") or request.args.get("hasta")

    fecha_desde = datetime.strptime(filtro_fecha_desde, "%Y-%m-%d") if filtro_fecha_desde else None
    fecha_hasta = datetime.strptime(filtro_fecha_hasta, "%Y-%m-%d") if filtro_fecha_hasta else None
    if fecha_hasta:
        fecha_hasta = fecha_hasta + timedelta(days=1)

    compras_query = Compra.query
    if filtro_estado:
        compras_query = compras_query.filter(Compra.estado == filtro_estado)
    if fecha_desde:
        compras_query = compras_query.filter(Compra.fecha >= fecha_desde)
    if fecha_hasta:
        compras_query = compras_query.filter(Compra.fecha < fecha_hasta)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    write_safe_csv_row(
        writer,
        [
            "compra_id",
            "usuario",
            "producto",
            "proveedor",
            "cantidad",
            "precio_unitario",
            "total",
            "estado",
            "fecha",
        ],
    )

    for compra in compras_query.order_by(Compra.fecha.desc()).all():
        write_safe_csv_row(
            writer,
            [
                compra.id,
                getattr(compra.usuario, "usuario", compra.usuario_id),
                getattr(compra.producto, "modelo", compra.producto_id),
                getattr(compra.proveedor, "nombre", compra.proveedor_id),
                compra.cantidad,
                f"{compra.precio_unitario}",
                f"{compra.total}",
                compra.estado,
                compra.fecha.strftime("%Y-%m-%d %H:%M") if hasattr(compra, "fecha") else "",
            ],
        )

    response = Response(buffer.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = "attachment; filename=compras_admin.csv"
    return response


@auth_bp.route('/eliminar_usuario/<string:usuario_id>', methods=['POST'])
@login_required
@role_required("admin")
def eliminar_usuario(usuario_id):
    # Usamos session.get para alinearnos con SQLAlchemy 2.x y evitar warnings de API legacy.
    usuario = db.session.get(Usuario, usuario_id)

    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('auth.actividades'))

    if usuario.id == current_user.id:
        flash("No puedes eliminar tu propia cuenta.", "danger")
        return redirect(url_for('auth.actividades'))

    try:
        db.session.delete(usuario)
        db.session.commit()

        registrar_actividad(
            usuario_id=current_user.id,
            accion=f"Eliminó al usuario {usuario.usuario} (ID: {usuario.id})",
            modulo="Gestión de Usuarios",
        )

        flash("Usuario eliminado correctamente.", "success")
    except Exception as exc:  # pragma: no cover - logs y feedback de usuario
        db.session.rollback()
        flash(f"Error al eliminar el usuario: {str(exc)}", "danger")

    return redirect(url_for('auth.actividades'))



@auth_bp.route('/cambiar_rol/<string:usuario_id>', methods=['POST'])
@login_required
@role_required("admin")
def cambiar_rol(usuario_id):
    """Permite actualizar el rol desde la vista admin.

    Regresa JSON cuando la petición se hace vía fetch (request.is_json) para
    evitar errores de parseo en el frontend; mantiene el flujo legacy de
    redirección/flash cuando llega un formulario tradicional.
    """

    def _responder(success: bool, message: str, category: str = "info", status: int = 200):
        if request.is_json:
            return jsonify({"success": success, "message": message}), status
        flash(message, category)
        return redirect(url_for('auth.actividades'))

    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return _responder(False, "Usuario no encontrado.", "danger", 404)

    payload = request.get_json(silent=True) or {}
    nuevo_rol = payload.get("rol") if request.is_json else request.form.get("rol")

    if usuario.id == current_user.id:
        return _responder(False, "No puedes cambiar tu propio rol.", "warning", 400)

    if nuevo_rol not in {"admin", "cliente"}:
        return _responder(False, "Rol inválido.", "danger", 400)

    try:
        usuario.rol = nuevo_rol
        db.session.commit()

        registrar_actividad(
            usuario_id=current_user.id,
            accion=f"Cambió rol de {usuario.usuario} a {nuevo_rol}",
            modulo="Gestión de Usuarios",
        )
    except Exception as exc:  # pragma: no cover - logs y feedback de usuario
        db.session.rollback()
        return _responder(False, f"Error al actualizar el rol: {exc}", "danger", 500)

    return _responder(True, "Rol cambiado correctamente.", "success")
