"""Blueprint de autenticación y administración de usuarios.

Agrupa las rutas de login/registro y acciones de administración para
reducir el monolito previo y documentar por qué se ajusta cada flujo.
"""

from flask import (
    Blueprint,
    current_app as app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ..db import db
from ..extensions import login_manager
from ..forms import Formulario_de_registro, Login_form
from ..models import ActividadUsuario, Compra, Usuario
from .helpers import registrar_actividad, role_required


auth_bp = Blueprint("auth", __name__)


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
            return redirect(url_for("auth.login"))

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
    app.logger.debug("Datos recibidos del formulario: %s", {**form.data, "contrasenya": "[omitted]"})

    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(usuario=form.usuario.data).first()

        # Validamos la existencia antes de acceder a atributos para evitar AttributeError.
        if not usuario:
            flash("Usuario o contraseña incorrectos.", "danger")
            return render_template("index.html", form=form)

        if usuario.check_contrasenya(form.contrasenya.data):
            login_user(usuario)
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


@auth_bp.route("/logout", methods=["POST", "GET"])
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

    if mensaje_exito:
        flash(mensaje_exito, "success")
    if mensaje_error:
        flash(mensaje_error, "danger")

    actividades = ActividadUsuario.query.order_by(ActividadUsuario.fecha.desc()).all()
    usuarios = Usuario.query.order_by(Usuario.fecha_registro.desc()).all()
    compras = Compra.query.order_by(Compra.fecha.desc()).all()

    return render_template("menu-admin.html", actividades=actividades, usuarios=usuarios, compras=compras)


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
    except Exception as exc:  # pragma: no cover - logs y feedback de usuario
        db.session.rollback()
        return _responder(False, f"Error al actualizar el rol: {exc}", "danger", 500)

    return _responder(True, "Rol cambiado correctamente.", "success")
