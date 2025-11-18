"""Pruebas básicas para los flujos de autenticación y compra.

Se usan fixtures ligeros en memoria para validar que las rutas críticas
soportan validaciones y commits atómicos.
"""

import os
import sys
import types
import unittest

from flask import url_for
from datetime import datetime

# Entorno de pruebas sin acceso a dependencias externas: inyectamos un stub
# mínimo de Flask-Migrate para que la factory pueda inicializarse sin fallar
# por importación. En despliegue real debe instalarse la librería oficial.
if "flask_migrate" not in sys.modules:
    flask_migrate = types.ModuleType("flask_migrate")

    class _DummyMigrate:  # pragma: no cover - solo evita errores en tests offline
        def __init__(self, *_, **__):
            ...

        def init_app(self, *_args, **_kwargs):
            ...

    flask_migrate.Migrate = _DummyMigrate
    sys.modules["flask_migrate"] = flask_migrate

from app import create_app
from app.db import db
from app.models import Usuario, Producto, Proveedor, CestaDeCompra, Compra


_TEST_APP = None


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        # Configuración aislada: BD en memoria y CSRF deshabilitado sólo para pruebas.
        os.environ["DATABASE_URI"] = "sqlite:///:memory:"
        os.environ["WTF_CSRF_ENABLED"] = "false"
        global _TEST_APP
        if _TEST_APP is None:
            _TEST_APP = create_app()
            _TEST_APP.config.update(TESTING=True)
        self.app = _TEST_APP
        self.client = self.app.test_client()
        rutas = {rule.rule for rule in self.app.url_map.iter_rules()}
        assert "/confirmar-compra" in rutas, rutas
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


class AuthFlowTest(BaseTestCase):
    def test_registration_and_login_redirects(self):
        """Valida que el registro crea el usuario y el login redirige según rol."""
        payload = {
            "nombre": "Usuario Test",
            "usuario": "tester",
            "direccion": "Calle Falsa 123",
            "contrasenya": "segura",
            "contrasenya2": "segura",
            "rol": "admin",
        }

        with self.app.app_context():
            response = self.client.post("/registro", data=payload, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(Usuario.query.filter_by(usuario="tester").first())

            login_resp = self.client.post(
                "/login",
                data={"usuario": "tester", "contrasenya": "segura"},
                follow_redirects=False,
            )
            self.assertEqual(login_resp.status_code, 302)
            self.assertIn("/menu_principal", login_resp.headers["Location"])

    def test_registration_validation_fails(self):
        """Un registro con contraseñas distintas no debería persistir usuario."""
        bad_payload = {
            "nombre": "Usuario Test",
            "usuario": "tester",
            "direccion": "Calle Falsa 123",
            "contrasenya": "segura",
            "contrasenya2": "otra",
            "rol": "cliente",
        }

        with self.app.app_context():
            resp = self.client.post("/registro", data=bad_payload, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(Usuario.query.count(), 0)


class CompraFlowTest(BaseTestCase):
    def _create_cliente_y_producto(self):
        proveedor = Proveedor(
            nombre="Proveedor Demo",
            telefono="123456789",
            direccion="Dirección demo",
            email="demo@example.com",
            cif="A1234567B",
            tasa_de_descuento=0,
            iva=21.0,
            tipo_producto="Procesador",
        )
        cliente = Usuario(
            nombre="Cliente",
            usuario="cliente1",
            direccion="Calle 1",
            contrasenya="segura",
            rol="cliente",
        )
        db.session.add_all([proveedor, cliente])
        db.session.flush()  # asegura IDs antes de crear dependencias

        producto = Producto(
            proveedor_id=proveedor.id,
            tipo_producto="Procesador",
            modelo="Modelo X",
            descripcion="",
            cantidad=2,
            cantidad_minima=0,
            precio=10.0,
            marca="Marca",
            num_referencia="REF-1",
        )
        db.session.add(producto)
        db.session.commit()
        return cliente, producto

    def test_confirmar_compra_atomics(self):
        """Verifica que confirmar compra descuenta inventario y limpia la cesta."""
        with self.app.app_context():
            cliente, producto = self._create_cliente_y_producto()
            cliente_id, producto_id = cliente.id, producto.id

            cesta_item = CestaDeCompra(
                usuario_id=cliente_id, producto_id=producto_id, cantidad=2
            )
            db.session.add(cesta_item)
            db.session.commit()

        # Inyectamos sesión autenticada para centrarnos en la lógica de compra.
        with self.client.session_transaction() as session:
            session["_user_id"] = cliente_id
            session["_fresh"] = True

        # Verificamos que la ruta esté registrada antes de llamar.
        rutas = {rule.rule for rule in self.app.url_map.iter_rules()}
        self.assertIn("/confirmar-compra", rutas)

        resp = self.client.post(
            "/confirmar-compra",
            data={"direccion": "Calle 1", "metodo_pago": "tarjeta"},
            follow_redirects=False,
        )
        self.assertEqual(
            resp.status_code,
            302,
            f"Respuesta inesperada {resp.status_code}: {resp.data[:120]}"
        )
        self.assertIn("/pedidos", resp.headers.get("Location", ""))

        with self.app.app_context():
            producto = db.session.get(Producto, producto_id)
            self.assertEqual(producto.cantidad, 0)
            self.assertEqual(CestaDeCompra.query.count(), 0)

    def test_confirma_compra_rechaza_stock_insuficiente(self):
        """Un pedido que supera el stock no crea registros ni descuenta inventario."""
        with self.app.app_context():
            proveedor = Proveedor(
                nombre="Proveedor Demo",
                telefono="123456789",
                direccion="Dirección demo",
                email="demo@example.com",
                cif="B1234567C",
                tasa_de_descuento=0,
                iva=21.0,
                tipo_producto="Procesador",
            )
            cliente = Usuario(
                nombre="Cliente",
                usuario="cliente_stock",
                direccion="Calle 1",
                contrasenya="segura",
                rol="cliente",
            )
            db.session.add_all([proveedor, cliente])
            db.session.flush()
            producto = Producto(
                proveedor_id=proveedor.id,
                tipo_producto="Procesador",
                modelo="Modelo XS",
                descripcion="",
                cantidad=1,
                cantidad_minima=0,
                precio=10.0,
                marca="Marca",
                num_referencia="REF-2",
            )
            db.session.add(producto)
            db.session.commit()
            producto_id = producto.id

        self.client.post(
            "/login",
            data={"usuario": "cliente_stock", "contrasenya": "segura"},
            follow_redirects=True,
        )
        self.client.post(
            f"/agregar_a_la_cesta/{producto_id}",
            data={"cantidad": 2},
            follow_redirects=True,
        )

        resp = self.client.post(
            "/confirmar-compra",
            data={"direccion": "Calle 1", "metodo_pago": "tarjeta"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            self.assertEqual(Compra.query.count(), 0)
            self.assertEqual(db.session.get(Producto, producto_id).cantidad, 1)


class DataEndpointsTest(BaseTestCase):
    def _crear_admin(self):
        admin = Usuario(
            nombre="Admin",
            usuario="admin1",
            direccion="Oficina",
            contrasenya="segura",
            rol="admin",
            fecha_registro=datetime(2024, 1, 1),
        )
        db.session.add(admin)
        db.session.commit()
        return admin

    def _login(self, user_id: str):
        # Se inyecta la sesión para saltar el login y enfocarnos en permisos de rol.
        with self.client.session_transaction() as session:
            session["_user_id"] = user_id
            session["_fresh"] = True

    def test_usuarios_registrados_requiere_auth_y_admin(self):
        resp = self.client.get("/data/usuarios_registrados", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers.get("Location", ""))

        with self.app.app_context():
            cliente = Usuario(
                nombre="Cliente",
                usuario="cliente_demo",
                direccion="Calle 1",
                contrasenya="segura",
                rol="cliente",
            )
            db.session.add(cliente)
            db.session.commit()
            self._login(cliente.id)

        resp_cliente = self.client.get("/data/usuarios_registrados")
        self.assertEqual(resp_cliente.status_code, 302)
        self.assertIn("/", resp_cliente.headers.get("Location", ""))

    def test_usuarios_registrados_agrupa_por_mes(self):
        with self.app.app_context():
            admin = self._crear_admin()
            usuarios = [
                Usuario(
                    nombre="Uno",
                    usuario="u1",
                    direccion="Calle 1",
                    contrasenya="segura",
                    rol="cliente",
                    fecha_registro=datetime(2024, 1, 10),
                ),
                Usuario(
                    nombre="Dos",
                    usuario="u2",
                    direccion="Calle 2",
                    contrasenya="segura",
                    rol="cliente",
                    fecha_registro=datetime(2024, 2, 5),
                ),
            ]
            db.session.add_all(usuarios)
            db.session.commit()
            self._login(admin.id)

        resp = self.client.get("/data/usuarios_registrados?interval=mes")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["periodos"], ["2024-01", "2024-02"])
        self.assertEqual(data["totales"], [2, 1])

    def test_ventas_totales_trimestre(self):
        with self.app.app_context():
            admin = self._crear_admin()
            cliente = Usuario(
                nombre="Cliente",
                usuario="cli1",
                direccion="Calle 1",
                contrasenya="segura",
                rol="cliente",
            )
            proveedor = Proveedor(
                nombre="Prov",
                telefono="123", direccion="Dir", email="p@example.com", cif="CIF12345", iva=21.0,
                tasa_de_descuento=0, tipo_producto="Procesador",
            )
            db.session.add_all([cliente, proveedor])
            db.session.flush()  # asegura IDs antes de crear el producto dependiente
            producto = Producto(
                proveedor_id=proveedor.id,
                tipo_producto="Procesador",
                modelo="M1",
                descripcion="",
                cantidad=10,
                cantidad_minima=0,
                precio=5.0,
                marca="Marca",
                num_referencia="REF-2",
            )
            db.session.add(producto)
            db.session.flush()  # fija el ID del producto antes de asociar compras
            compra_q1 = Compra(producto_id=producto.id, usuario_id=cliente.id, proveedor_id=proveedor.id, cantidad=1, precio_unitario=5.0, total=5.0, fecha=datetime(2024, 1, 15))
            compra_q2 = Compra(producto_id=producto.id, usuario_id=cliente.id, proveedor_id=proveedor.id, cantidad=2, precio_unitario=5.0, total=10.0, fecha=datetime(2024, 4, 10))
            db.session.add_all([cliente, proveedor, producto, compra_q1, compra_q2])
            db.session.commit()
            self._login(admin.id)

        resp = self.client.get("/data/ventas_totales?interval=trimestre")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["periodos"], ["2024-T1", "2024-T2"])
        self.assertEqual(data["totales"], [5.0, 10.0])


class AdminCrudTest(BaseTestCase):
    def _login_admin(self):
        with self.app.app_context():
            admin = Usuario(
                nombre="Admin",
                usuario="admin_crud",
                direccion="Oficina",
                contrasenya="segura",
                rol="admin",
            )
            db.session.add(admin)
            db.session.commit()

        self.client.post(
            "/login",
            data={"usuario": "admin_crud", "contrasenya": "segura"},
            follow_redirects=True,
        )

    def test_admin_crea_proveedor_y_producto(self):
        self._login_admin()

        proveedor_payload = {
            "nombre": "Proveedor QA",
            "telefono": "987654321",
            "direccion": "Direccion QA",
            "email": "qa@example.com",
            "cif": "CIFQA1",
            "tasa_de_descuento": "0",
            "iva": "21",
            "productos": ["Procesador"],
        }

        resp_prov = self.client.post("/agregar-proveedor", data=proveedor_payload, follow_redirects=True)
        self.assertEqual(resp_prov.status_code, 200)

        with self.app.app_context():
            proveedor = Proveedor.query.filter_by(cif="CIFQA1").first()
            self.assertIsNotNone(proveedor)

        producto_payload = {
            "proveedor_id": proveedor.id,
            "tipo_producto": "Procesador",
            "modelo": "Modelo QA",
            "descripcion": "",
            "cantidad": 5,
            "cantidad_minima": 1,
            "precio": 2.5,
            "marca": "Intel",
            "num_referencia": "QA-1",
        }

        resp_prod = self.client.post("/agregar-producto", data=producto_payload, follow_redirects=True)
        self.assertEqual(resp_prod.status_code, 200)

        with self.app.app_context():
            producto = Producto.query.filter_by(modelo="Modelo QA").first()
            self.assertIsNotNone(producto)
            self.assertEqual(producto.proveedor_id, proveedor.id)


class AdminCrudTest(BaseTestCase):
    """Cobertura básica para ediciones y eliminaciones con CSRF activo en plantillas."""

    def setUp(self):
        super().setUp()
        with self.app.app_context():
            admin = Usuario(nombre="Admin", usuario="admin", direccion="Calle Admin", contrasenya="segura", rol="admin")
            proveedor = Proveedor(
                nombre="Proveedor CRUD",
                telefono="111111111",
                direccion="Dirección CRUD",
                email="crud@example.com",
                cif="CRUD-1",
                tasa_de_descuento=0,
                iva=21.0,
                tipo_producto="CPU",
            )
            db.session.add_all([admin, proveedor])
            db.session.flush()
            producto = Producto(
                proveedor_id=proveedor.id,
                tipo_producto="CPU",
                modelo="Viejo Modelo",
                descripcion="",
                cantidad=3,
                cantidad_minima=1,
                precio=10.0,
                marca="Marca",
                num_referencia="REF-CRUD",
            )
            db.session.add(producto)
            db.session.commit()
            self.admin_id = admin.id
            self.proveedor_id = proveedor.id
            self.producto_id = producto.id

        # Login admin para habilitar rutas protegidas.
        self.client.post("/login", data={"usuario": "admin", "contrasenya": "segura"}, follow_redirects=True)

    def test_editar_y_eliminar_producto(self):
        nuevo_payload = {
            "descripcion": "Actualizado",
            "cantidad": 7,
            "cantidad_minima": 2,
            "precio": 12.5,
            "num_referencia": "REF-ACT",
        }
        resp_edit = self.client.post(f"/editar_producto/{self.producto_id}", data=nuevo_payload, follow_redirects=True)
        self.assertEqual(resp_edit.status_code, 200)
        with self.app.app_context():
            producto = db.session.get(Producto, self.producto_id)
            self.assertEqual(producto.descripcion, "Actualizado")
            self.assertEqual(producto.cantidad, 7)

        resp_delete = self.client.post(f"/eliminar_producto/{self.producto_id}", follow_redirects=True)
        self.assertEqual(resp_delete.status_code, 200)
        with self.app.app_context():
            self.assertEqual(Producto.query.count(), 0)

    def test_editar_y_eliminar_proveedor(self):
        edit_payload = {
            "nombre": "Proveedor Editado",
            "telefono": "222222222",
            "direccion": "Dirección Editada",
            "email": "edit@example.com",
            "cif": "CRUD-EDIT",
            "tasa_de_descuento": "5",
            "iva": "18",
            "tipo_producto": "RAM",
            "productos": ["RAM"],
        }
        resp_edit = self.client.post(f"/editar_proveedor/{self.proveedor_id}", data=edit_payload, follow_redirects=True)
        self.assertEqual(resp_edit.status_code, 200)
        with self.app.app_context():
            proveedor = db.session.get(Proveedor, self.proveedor_id)
            self.assertEqual(proveedor.nombre, "Proveedor Editado")
            self.assertEqual(proveedor.tipo_producto, "RAM")

        resp_delete = self.client.post(f"/eliminar_proveedor/{self.proveedor_id}", follow_redirects=True)
        self.assertEqual(resp_delete.status_code, 200)
        with self.app.app_context():
            self.assertEqual(Proveedor.query.count(), 0)


class PerfilClienteTest(BaseTestCase):
    def test_actualizar_perfil_cliente(self):
        with self.app.app_context():
            cliente = Usuario(
                nombre="Cliente", usuario="cliente_mod", direccion="Calle 1", contrasenya="segura", rol="cliente"
            )
            db.session.add(cliente)
            db.session.commit()

        self.client.post("/login", data={"usuario": "cliente_mod", "contrasenya": "segura"}, follow_redirects=True)
        resp = self.client.post(
            "/perfil_cliente",
            data={"nombre_usuario": "Cliente Editado", "direccion": "Nueva Direccion"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        with self.app.app_context():
            cliente = Usuario.query.filter_by(usuario="cliente_mod").first()
            self.assertEqual(cliente.nombre, "Cliente Editado")
            self.assertEqual(cliente.direccion, "Nueva Direccion")


if __name__ == "__main__":
    unittest.main()
