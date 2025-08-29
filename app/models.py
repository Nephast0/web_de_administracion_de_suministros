import secrets
from datetime import datetime
import bcrypt
from flask_login import UserMixin
from sqlalchemy import Column, String, Float
from .db import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])  # ID corto de 8 caracteres
    nombre = Column(String, nullable=False)
    usuario = Column(String(25), nullable=False)
    direccion = Column(String(), nullable=False)
    contrasenya_hash = Column(String(100), nullable=False)
    rol = Column(String(), nullable= False)
    fecha_registro = Column(db.DateTime,nullable=False, default=datetime.utcnow())

    def hash_contrasenya(self, contrasenya):
        self.contrasenya_hash = bcrypt.hashpw(
            contrasenya.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    def check_contrasenya(self, contrasenya):
        return bcrypt.checkpw(
            contrasenya.encode("utf-8"),
            self.contrasenya_hash.encode("utf-8"))

    def __init__(self,nombre, usuario, direccion, contrasenya, rol, fecha_registro = None):
        self.nombre = nombre
        self.usuario = usuario
        self.direccion = direccion
        self.hash_contrasenya(contrasenya)
        self.rol = rol
        self.fecha_registro= fecha_registro or datetime.utcnow()

    def __str__(self):
        return f"Usuario {self.usuario} creado con éxito."

class Producto(db.Model):
    __tablename__ = "producto"

    id = db.Column(db.String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])
    proveedor_id = db.Column(db.String(), db.ForeignKey('proveedor.id'), nullable=False)
    tipo_producto = db.Column(db.String(), nullable=False)
    modelo = db.Column(db.String(), nullable=False)
    descripcion = db.Column(db.String(), nullable=True)
    cantidad = db.Column(db.Integer, nullable=False)
    cantidad_minima = db.Column(db.Integer, nullable=True)
    precio = db.Column(db.Float, nullable=False)
    marca = db.Column(db.String(), nullable=True)
    num_referencia = db.Column(db.String(), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, proveedor_id, tipo_producto, modelo, descripcion, cantidad, cantidad_minima, precio, marca, num_referencia, fecha=None):
        self.proveedor_id = proveedor_id
        self.tipo_producto = tipo_producto
        self.modelo = modelo
        self.descripcion = descripcion
        self.cantidad = cantidad
        self.cantidad_minima = cantidad_minima
        self.precio = precio
        self.marca = marca
        self.num_referencia = num_referencia
        self.fecha = fecha or datetime.utcnow()

    def __str__(self):
        return f"{self.modelo} se ha agregado correctamente."

class Proveedor(db.Model):
    __tablename__ = "proveedor"

    id = Column(String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])  # ID corto de 8 caracteres
    nombre = Column(String(25), nullable=False)
    telefono = Column(String(), nullable=False)
    direccion = Column(String(), nullable=False)
    email = Column(String(), nullable=False)
    cif = Column(String(), nullable=False, unique=True)  # Campo único para evitar duplicados
    tasa_de_descuento = Column(Float, nullable=False)
    iva = Column(Float, nullable=False)
    tipo_producto = db.Column(db.String(500), nullable=False)  # Asegúrate de usar un tamaño suficiente
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    productos = db.relationship('ProveedorTipoProducto', back_populates='proveedor')

    def __init__(self, nombre, telefono, direccion, email, cif, tasa_de_descuento, iva,tipo_producto, fecha=None):
        self.nombre = nombre
        self.telefono = telefono
        self.direccion = direccion
        self.email = email
        self.cif = cif
        self.tasa_de_descuento = tasa_de_descuento
        self.iva = iva
        self.tipo_producto = tipo_producto
        self.fecha = fecha or datetime.utcnow()

    def __str__(self):
        return f"Proveedor {self.nombre} agregado correctamente."

class ProveedorTipoProducto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.String, db.ForeignKey('proveedor.id'), nullable=False)
    producto_id = db.Column(db.String, db.ForeignKey('producto.id'), nullable=False)
    # Relaciones
    proveedor = db.relationship('Proveedor', backref='tipo_productos')
    producto = db.relationship('Producto', backref='tipo_proveedores')

class CestaDeCompra(db.Model):
    __tablename__ = "cesta_de_compra"

    id = Column(String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])
    usuario_id = db.Column(db.String, db.ForeignKey('usuario.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

    # Relaciones
    usuario = db.relationship('Usuario', backref=db.backref('cesta_de_compra', lazy=True))
    producto = db.relationship('Producto', backref=db.backref('cesta_de_compra', lazy=True))

    def __init__(self, usuario_id, producto_id, cantidad=1):
        self.usuario_id = usuario_id
        self.producto_id = producto_id
        self.cantidad = cantidad

class Compra(db.Model):
    __tablename__ = "compras"

    id = db.Column(db.String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])  # ID corto de 8 caracteres
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)  # Producto comprado
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Usuario que realizó la compra
    cantidad = db.Column(db.Integer, nullable=False)  # Cantidad comprada
    precio_unitario = db.Column(db.Float, nullable=False)  # Precio unitario en el momento de la compra
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedor.id'), nullable=False)  # Proveedor relacionado
    total = db.Column(db.Float, nullable=False)  # Total de la compra
    estado = db.Column(db.String(20), nullable=False, default="Pendiente")  # Estado de la compra
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Fecha de la acción

    # Relaciones
    producto = db.relationship('Producto', backref=db.backref('compras', lazy=True))
    proveedor = db.relationship('Proveedor', backref=db.backref('compras', lazy=True))
    usuario = db.relationship('Usuario', backref=db.backref('compras', lazy=True))

    def __init__(self, producto_id, usuario_id, cantidad, precio_unitario, proveedor_id, total, estado="Pendiente", fecha=None):
        self.producto_id = producto_id
        self.usuario_id = usuario_id
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario
        self.proveedor_id = proveedor_id
        self.total = total
        self.estado = estado
        self.fecha = fecha or datetime.utcnow()

class ActividadUsuario(db.Model):
    __tablename__= "actividad_usuario"
    id = Column(String(8), primary_key=True, default=lambda: secrets.token_hex(4)[:8])  # ID corto de 8 caracteres
    usuario_id = db.Column(db.String(8), db.ForeignKey('usuario.id'), nullable=False)  # Relación con la tabla Usuario
    accion = db.Column(db.String(200), nullable=False)  # Descripción de la acción
    modulo = db.Column(db.String(100), nullable=False)  # Módulo o funcionalidad
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Fecha de la acción

    # Relación con el usuario
    usuario = db.relationship('Usuario', backref='actividades')

    def __repr__(self):
        return f'<ActividadUsuario {self.accion} - {self.modulo}>'