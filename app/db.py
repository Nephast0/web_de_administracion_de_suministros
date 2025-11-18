"""Instancia de base de datos para compartir en toda la app."""

from flask_sqlalchemy import SQLAlchemy

# Instancia global inicializada en create_app.
db = SQLAlchemy()
