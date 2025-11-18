"""Aplicación principal y configuración inicial.

Este módulo prepara la factory de Flask y centraliza la configuración
para mantener fuera del código duro credenciales sensibles. También
se documentan los motivos de cada ajuste para facilitar futuras
revisiones.
"""

import logging
import os
from flask import Flask

from .db import db
from .extensions import csrf, login_manager, bcrypt
from .blueprints import register_blueprints
from flask_migrate import Migrate


# Instancia global de Flask-Migrate; se inicializa dentro de create_app.
migrate = Migrate()


def _get_bool_env(var_name: str, default: bool) -> bool:
    """Convierte variables de entorno en booleanos de forma segura."""
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y"}


def create_app():
    """Factory de la aplicación Flask.

    Se aplica la configuración desde variables de entorno para no
    exponer claves ni activar depuración/verborrea SQL sin querer.
    """

    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Logging básico para depurar en desarrollo. Se puede ajustar por
    # entorno configurando LOG_LEVEL en despliegue.
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Configuración leída desde entorno con valores seguros por defecto.
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URI", "sqlite:///../instance/administracion.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # El eco de SQL queda desactivado salvo que se habilite explícitamente
    # via env para evitar ruido/logs sensibles en producción.
    app.config["SQLALCHEMY_ECHO"] = _get_bool_env("SQLALCHEMY_ECHO", False)
    # Se usa SECRET_KEY desde entorno; se mantiene un fallback mínimo
    # sólo para desarrollo local.
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cambia-esta-clave")
    # CSRF activado por defecto para formularios; se puede desactivar
    # temporalmente con WTF_CSRF_ENABLED=false en entorno de pruebas.
    app.config["WTF_CSRF_ENABLED"] = _get_bool_env("WTF_CSRF_ENABLED", True)

    # Inicializar extensiones con la app actual.
    db.init_app(app)
    bcrypt.init_app(app)
    # Activamos protección CSRF global para evitar envíos sin token; puede
    # deshabilitarse en pruebas automatizadas vía WTF_CSRF_ENABLED=false.
    csrf.init_app(app)
    login_manager.init_app(app)
    # Con blueprints activamos la vista de login bajo el namespace de auth.
    login_manager.login_view = "auth.login"

    # Inicializar Flask-Migrate para futuras migraciones.
    migrate.init_app(app, db)

    # Registrar modelos y blueprints dentro del contexto para evitar imports
    # circulares y mantener la inicialización documentada.
    with app.app_context():
        from . import models  # noqa: F401
        register_blueprints(app)

    # Se retorna la instancia correctamente (el código anterior estaba
    # truncado), permitiendo a run.py u otros módulos inicializar la app.
    return app
