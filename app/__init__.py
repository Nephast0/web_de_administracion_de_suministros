"""Aplicación principal y configuración inicial.

Este módulo prepara la factory de Flask y centraliza la configuración
para mantener fuera del código duro credenciales sensibles. También
se documentan los motivos de cada ajuste para facilitar futuras
revisiones.
"""

import logging
import os
from decimal import Decimal, InvalidOperation

from babel.core import UnknownLocaleError
from babel.numbers import format_currency as babel_currency, get_currency_symbol
from flask import Flask, current_app

from .db import db
from .extensions import csrf, login_manager, bcrypt
from .blueprints import register_blueprints
from flask_migrate import Migrate


# Instancia global de Flask-Migrate; se inicializa dentro de create_app.
migrate = Migrate()
_DEFAULT_CURRENCY_CODE = os.getenv("CURRENCY_CODE", "EUR")
_DEFAULT_CURRENCY_LOCALE = os.getenv("CURRENCY_LOCALE", "es_ES")
_DEFAULT_CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL")


def _get_bool_env(var_name: str, default: bool) -> bool:
    """Convierte variables de entorno en booleanos de forma segura."""
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y"}


def _currency_config(app=None):
    """Obtiene la configuración activa de moneda a partir de app o entorno."""

    config = {
        "code": _DEFAULT_CURRENCY_CODE,
        "locale": _DEFAULT_CURRENCY_LOCALE,
        "symbol": _DEFAULT_CURRENCY_SYMBOL,
    }
    target_app = app
    if target_app is None:
        try:
            target_app = current_app._get_current_object()
        except RuntimeError:
            target_app = None
    if target_app is not None:
        config["code"] = target_app.config.get("CURRENCY_CODE", config["code"])
        config["locale"] = target_app.config.get("CURRENCY_LOCALE", config["locale"])
        config["symbol"] = target_app.config.get("CURRENCY_SYMBOL", config["symbol"])
    return config


def _resolve_currency_symbol(currency_code=None, locale=None, explicit_symbol=None):
    """Resuelve el símbolo a mostrar combinando overrides, locale y código."""

    if explicit_symbol:
        return explicit_symbol
    config = _currency_config()
    code = currency_code or config["code"]
    locale_name = locale or config["locale"]
    try:
        return get_currency_symbol(code, locale=locale_name)
    except (UnknownLocaleError, ValueError):
        return code


def format_currency(value, symbol: str | None = None, currency_code: str | None = None, locale: str | None = None) -> str:
    """Convierte valores numéricos en cantidades legibles respetando el locale."""

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value

    config = _currency_config()
    code = currency_code or config["code"]
    locale_name = locale or config["locale"]
    symbol_override = symbol or config["symbol"]

    try:
        formatted = babel_currency(amount, code, locale=locale_name, format="¤#,##0.00")
    except (UnknownLocaleError, ValueError):
        formatted_amount = f"{amount:,.2f}"
        formatted_amount = formatted_amount.replace(",", "X").replace(".", ",").replace("X", ".")
        resolved_symbol = _resolve_currency_symbol(code, locale_name, symbol_override)
        return f"{resolved_symbol}{formatted_amount}"

    if symbol_override:
        try:
            default_symbol = get_currency_symbol(code, locale=locale_name)
        except (UnknownLocaleError, ValueError):
            default_symbol = ""
        if default_symbol and default_symbol in formatted:
            formatted = formatted.replace(default_symbol, symbol_override, 1)
        else:
            formatted = f"{symbol_override}{formatted}"

    return formatted


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
    app.config.setdefault("CURRENCY_CODE", _DEFAULT_CURRENCY_CODE)
    app.config.setdefault("CURRENCY_LOCALE", _DEFAULT_CURRENCY_LOCALE)
    app.config.setdefault("CURRENCY_SYMBOL", _DEFAULT_CURRENCY_SYMBOL)

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
    # render_as_batch=True es necesario para SQLite que no soporta ALTER TABLE completamente.
    migrate.init_app(app, db, render_as_batch=True)


    # Registrar filtros compartidos antes de exponer las vistas.
    app.jinja_env.filters["currency"] = format_currency

    # Registrar modelos y blueprints dentro del contexto para evitar imports
    # circulares y mantener la inicialización documentada.
    with app.app_context():
        from . import models  # noqa: F401
        register_blueprints(app)

    @app.context_processor
    def inject_currency_meta():
        config = _currency_config(app)
        return {
            "currency_symbol": _resolve_currency_symbol(
                config["code"], config["locale"], config["symbol"]
            ),
            "currency_locale": config["locale"],
            "currency_code": config["code"],
        }

    # Se retorna la instancia correctamente (el código anterior estaba
    # truncado), permitiendo a run.py u otros módulos inicializar la app.
    return app
