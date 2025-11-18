"""Inicialización centralizada de extensiones Flask."""

from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Las instancias se crean aquí y se inicializan en create_app para evitar
# dependencias circulares en tiempo de importación.
login_manager = LoginManager()
bcrypt = Bcrypt()
# CSRFProtect se expone como extensión para reutilizarla en tests o futuras
# vistas API; mantenerlo aquí evita inicializaciones parciales.
csrf = CSRFProtect()
