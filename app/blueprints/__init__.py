"""Registro centralizado de blueprints.

Dividimos las rutas en módulos temáticos para reducir el monolito previo
(`routes.py`) y facilitar pruebas por área.
"""

from flask import Flask

from .auth import auth_bp
from .inventario import inventario_bp
from .proveedores import proveedores_bp
from .reportes import reportes_bp


def register_blueprints(app: Flask) -> None:
    """Adjunta todos los blueprints a la aplicación Flask.

    Se deja en una función separada para mantener `create_app` limpio y para
    documentar qué módulos se cargan durante el arranque.
    """

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(proveedores_bp)
    app.register_blueprint(reportes_bp)
