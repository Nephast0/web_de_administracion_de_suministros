import logging
from flask import Flask
from .db import db
from .extensions import login_manager, bcrypt
from flask_migrate import Migrate

migrate = Migrate()   # instancia global

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Logging básico
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Configuración
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../instance/administracion.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = True
    app.config["SECRET_KEY"] = "ad877c"
    app.config["WTF_CSRF_ENABLED"] = False

    # Inicializar extensiones
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"

    # Inicializar Flask-Migrate
    migrate.init_app(app, db)

    # Registrar rutas
    with app.app_context():
        from . import models
        from . import routes
        # ⚠️ solo si quieres: db.create_all()
        # pero ojo: mejor hacerlo en un script separado

    return app