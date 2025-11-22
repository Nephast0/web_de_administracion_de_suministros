"""Modelos de datos y utilidades de autenticación.

Los cambios se comentan inline para explicar las decisiones tomadas
en cuanto a seguridad y consistencia de datos.
"""

import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import ForeignKey

from .db import db
from .extensions import bcrypt


def utcnow():
    """Retorna instantes timezone-aware para evitar warnings de SQLAlchemy."""
    return datetime.now(timezone.utc)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"
    __table_args__ = {"sqlite_autoincrement": True}

    # IDs cortos de 8 caracteres para legibilidad, pero no autoincrementales.
    id = db.Column(db.String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])
    # Se fijan longitudes y unicidad para evitar duplicados y truncados.
    nombre = db.Column(db.String(80), nullable=False)
    usuario = db.Column(db.String(50), nullable=False, unique=True)
    direccion = db.Column(db.String(150), nullable=False)
    contrasenya_hash = db.Column(db.String(128), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=utcnow)

    def hash_contrasenya(self, contrasenya: str) -> None:
        """Genera un hash usando flask-bcrypt configurado en la app."""
        # Se usa la extensión configurada en lugar de la librería directa
        # para honrar los parámetros globales (por ejemplo, rounds).
        self.contrasenya_hash = bcrypt.generate_password_hash(contrasenya).decode("utf-8")

    def check_contrasenya(self, contrasenya: str) -> bool:
        """Valida la contraseña usando el hash almacenado."""
        return bcrypt.check_password_hash(self.contrasenya_hash, contrasenya)

    def __init__(self, nombre, usuario, direccion, contrasenya, rol, fecha_registro=None):
        self.nombre = nombre
        self.usuario = usuario
        self.direccion = direccion
        # Se delega en el método que aplica bcrypt configurado.
        self.hash_contrasenya(contrasenya)
        self.rol = rol
        # Fecha por defecto calculada en Python para mantener trazabilidad.
        self.fecha_registro = fecha_registro or utcnow()

    def __str__(self):
        return f"Usuario {self.usuario} creado con éxito."


class Producto(db.Model):
    __tablename__ = "producto"

    id = db.Column(db.String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])
    # Claves foráneas tipadas como String para alinearse con el ID del proveedor.
    proveedor_id = db.Column(db.String(8), db.ForeignKey("proveedor.id"), nullable=False)
    tipo_producto = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(500), nullable=True)
    cantidad = db.Column(db.Integer, nullable=False)
    cantidad_minima = db.Column(db.Integer, nullable=True)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    costo = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    marca = db.Column(db.String(100), nullable=True)
    num_referencia = db.Column(db.String(80), nullable=False)
    fecha = db.Column(db.DateTime, default=utcnow, nullable=False)

    # Enlazamos explícitamente la tabla pivote para evitar warnings de relaciones solapadas.
    proveedor_links = db.relationship("ProveedorTipoProducto", back_populates="producto", cascade="all, delete-orphan")

    def __init__(self, proveedor_id, tipo_producto, modelo, descripcion, cantidad, cantidad_minima, precio, marca, num_referencia, costo=0.00, fecha=None):
        self.proveedor_id = proveedor_id
        self.tipo_producto = tipo_producto
        self.modelo = modelo
        self.descripcion = descripcion
        self.cantidad = cantidad
        self.cantidad_minima = cantidad_minima
        self.precio = precio
        self.costo = costo
        self.marca = marca
        self.num_referencia = num_referencia
        self.fecha = fecha or utcnow()

    def __str__(self):
        return f"{self.modelo} se ha agregado correctamente."


class Proveedor(db.Model):
    __tablename__ = "proveedor"

    id = db.Column(db.String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(15), nullable=False)
    direccion = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    cif = db.Column(db.String(15), nullable=False, unique=True)  # único para evitar duplicados.
    tasa_de_descuento = db.Column(db.Numeric(10, 2), nullable=True)
    iva = db.Column(db.Numeric(10, 2), nullable=False)
    tipo_producto = db.Column(db.String(500), nullable=False)
    fecha = db.Column(db.DateTime, default=utcnow, nullable=False)

    # Se usan back_populates simétricos para eliminar el warning de overlaps.
    productos = db.relationship(
        "ProveedorTipoProducto",
        back_populates="proveedor",
        cascade="all, delete-orphan",
    )

    def __init__(self, nombre, telefono, direccion, email, cif, tasa_de_descuento, iva, tipo_producto, fecha=None):
        self.nombre = nombre
        self.telefono = telefono
        self.direccion = direccion
        self.email = email
        self.cif = cif
        self.tasa_de_descuento = tasa_de_descuento
        self.iva = iva
        self.tipo_producto = tipo_producto
        self.fecha = fecha or utcnow()

    def __str__(self):
        return f"Proveedor {self.nombre} agregado correctamente."


class ProveedorTipoProducto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.String(8), db.ForeignKey("proveedor.id"), nullable=False)
    producto_id = db.Column(db.String(8), db.ForeignKey("producto.id"), nullable=False)
    # Relaciones explícitas para claridad en consultas sin generar overlaps.
    proveedor = db.relationship("Proveedor", back_populates="productos")
    producto = db.relationship("Producto", back_populates="proveedor_links")


class CestaDeCompra(db.Model):
    __tablename__ = "cesta_de_compra"

    id = db.Column(db.String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])
    usuario_id = db.Column(db.String(8), db.ForeignKey("usuario.id"), nullable=False)
    # Se homologa el tipo con Producto.id para integridad referencial.
    producto_id = db.Column(db.String(8), db.ForeignKey("producto.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

    usuario = db.relationship("Usuario", backref=db.backref("cesta_de_compra", lazy=True))
    producto = db.relationship("Producto", backref=db.backref("cesta_de_compra", lazy=True))

    def __init__(self, usuario_id, producto_id, cantidad=1):
        self.usuario_id = usuario_id
        self.producto_id = producto_id
        self.cantidad = cantidad


class Compra(db.Model):
    __tablename__ = "compras"

    id = db.Column(db.String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])
    # Claves foráneas alineadas con los IDs de tipo String definidos en las tablas.
    producto_id = db.Column(db.String(8), db.ForeignKey("producto.id"), nullable=False)
    usuario_id = db.Column(db.String(8), db.ForeignKey("usuario.id"), nullable=False)
    proveedor_id = db.Column(db.String(8), db.ForeignKey("proveedor.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="Pendiente")
    fecha = db.Column(db.DateTime, default=utcnow, nullable=False)

    producto = db.relationship("Producto", backref=db.backref("compras", lazy=True))
    proveedor = db.relationship("Proveedor", backref=db.backref("compras", lazy=True))
    usuario = db.relationship("Usuario", backref=db.backref("compras", lazy=True))

    def __init__(self, producto_id, usuario_id, cantidad, precio_unitario, proveedor_id, total, estado="Pendiente", fecha=None):
        self.producto_id = producto_id
        self.usuario_id = usuario_id
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario
        self.proveedor_id = proveedor_id
        self.total = total
        self.estado = estado
        self.fecha = fecha or utcnow()


class ActividadUsuario(db.Model):
    __tablename__ = "actividad_usuario"
    id = db.Column(db.String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])
    usuario_id = db.Column(db.String(8), db.ForeignKey("usuario.id"), nullable=False)
    accion = db.Column(db.String(200), nullable=False)
    modulo = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.DateTime, default=utcnow, nullable=False)

    usuario = db.relationship("Usuario", backref="actividades")

    def __repr__(self):
        return f"<ActividadUsuario {self.accion} - {self.modulo}>"


# --- Modelos de Contabilidad (Doble Partida) ---

class Cuenta(db.Model):
    __tablename__ = "cuenta"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    # Tipos: 'ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO'
    tipo = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"<Cuenta {self.codigo} - {self.nombre}>"


class Asiento(db.Model):
    __tablename__ = "asiento"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=utcnow, nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    usuario_id = db.Column(db.String(8), db.ForeignKey("usuario.id"), nullable=False)
    referencia_id = db.Column(db.String(50), nullable=True)

    usuario = db.relationship("Usuario", backref="asientos")
    apuntes = db.relationship("Apunte", back_populates="asiento", cascade="all, delete-orphan")

    def __init__(self, descripcion, usuario_id, referencia_id=None, fecha=None):
        self.descripcion = descripcion
        self.usuario_id = usuario_id
        self.referencia_id = referencia_id
        self.fecha = fecha or utcnow()


class Apunte(db.Model):
    __tablename__ = "apunte"
    id = db.Column(db.Integer, primary_key=True)
    asiento_id = db.Column(db.Integer, db.ForeignKey("asiento.id"), nullable=False)
    cuenta_id = db.Column(db.Integer, db.ForeignKey("cuenta.id"), nullable=False)
    debe = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    haber = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)

    asiento = db.relationship("Asiento", back_populates="apuntes")
    cuenta = db.relationship("Cuenta", backref="apuntes")

    def __init__(self, cuenta_id, debe=0.00, haber=0.00):
        self.cuenta_id = cuenta_id
        self.debe = debe
        self.haber = haber
