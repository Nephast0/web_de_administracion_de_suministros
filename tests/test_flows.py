"""Pruebas básicas para los flujos de autenticación y compra.

Se usan fixtures ligeros en memoria para validar que las rutas críticas
soportan validaciones y commits atómicos.
"""

import json
import os
import secrets
import sys
import types
import unittest
from pathlib import Path

from flask import url_for
from datetime import datetime, timezone
from werkzeug.datastructures import MultiDict

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
from app.models import Usuario, Producto, Proveedor, CestaDeCompra, Compra, Asiento
from app.services.accounting_services import inicializar_plan_cuentas, crear_asiento


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
            "contrasenya": "Segura123!",
            "contrasenya2": "Segura123!",
        }

        with self.app.app_context():
            response = self.client.post("/registro", data=payload, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            nuevo_usuario = Usuario.query.filter_by(usuario="tester").first()
            self.assertIsNotNone(nuevo_usuario)
            self.assertEqual(nuevo_usuario.rol, "cliente")

            login_resp = self.client.post(
                "/login",
                data={"usuario": "tester", "contrasenya": "Segura123!"},
                follow_redirects=False,
            )
            self.assertEqual(login_resp.status_code, 302)
            self.assertIn("/menu-cliente", login_resp.headers["Location"])

    def test_registration_validation_fails(self):
        """Un registro con contraseñas distintas no debería persistir usuario."""
        bad_payload = {
            "nombre": "Usuario Test",
            "usuario": "tester",
            "direccion": "Calle Falsa 123",
            "contrasenya": "Segura123!",
            "contrasenya2": "Otra123!",
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
            contrasenya="Segura123!",
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
                contrasenya="Segura123!",
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
            data={"usuario": "cliente_stock", "contrasenya": "Segura123!"},
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

    def test_cesta_renderiza_con_alias_correcto(self):
        with self.app.app_context():
            cliente, _ = self._create_cliente_y_producto()
            cliente_id = cliente.id

        with self.client.session_transaction() as session:
            session["_user_id"] = cliente_id
            session["_fresh"] = True

        resp = self.client.get("/cesta")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Cesta", resp.data)

    def test_productos_cliente_soporta_cantidad_minima_null(self):
        with self.app.app_context():
            proveedor = Proveedor(
                nombre="Proveedor Null",
                telefono="123456789",
                direccion="Direccion demo",
                email="null@example.com",
                cif="C1234567Z",
                tasa_de_descuento=0,
                iva=21.0,
                tipo_producto="Procesador",
            )
            cliente = Usuario(
                nombre="Cliente Null",
                usuario="cliente_null",
                direccion="Calle 123",
                contrasenya="Segura123!",
                rol="cliente",
            )
            db.session.add_all([proveedor, cliente])
            db.session.flush()
            producto = Producto(
                proveedor_id=proveedor.id,
                tipo_producto="Procesador",
                modelo="Modelo Null",
                descripcion="",
                cantidad=5,
                cantidad_minima=None,
                precio=15.0,
                marca="Marca",
                num_referencia="REF-NULL",
            )
            db.session.add(producto)
            db.session.commit()

        self.client.post("/login", data={"usuario": "cliente_null", "contrasenya": "Segura123!"}, follow_redirects=True)
        resp = self.client.get("/productos_cliente")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Cat\xc3\xa1logo", resp.data)


class ClienteGraficasTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        with self.app.app_context():
            self.proveedor = Proveedor(
                nombre="Proveedor Charts",
                telefono="123456789",
                direccion="Ruta 1",
                email="charts@example.com",
                cif="C1234567D",
                tasa_de_descuento=0,
                iva=21.0,
                tipo_producto="Procesador",
            )
            db.session.add(self.proveedor)
            db.session.flush()

            self.producto_a = Producto(
                proveedor_id=self.proveedor.id,
                tipo_producto="Procesador",
                modelo="CPU-A",
                descripcion="",
                cantidad=10,
                cantidad_minima=0,
                precio=50.0,
                marca="Marca",
                num_referencia="CPU-A",
            )
            self.producto_b = Producto(
                proveedor_id=self.proveedor.id,
                tipo_producto="Procesador",
                modelo="CPU-B",
                descripcion="",
                cantidad=10,
                cantidad_minima=0,
                precio=70.0,
                marca="Marca",
                num_referencia="CPU-B",
            )
            self.cliente = Usuario(
                nombre="Cliente Charts",
                usuario="clienteCharts",
                direccion="Calle Graf",
                contrasenya="Segura123!",
                rol="cliente",
            )
            db.session.add_all([self.producto_a, self.producto_b, self.cliente])
            db.session.commit()
            self.proveedor_id = self.proveedor.id
            self.producto_a_id = self.producto_a.id
            self.producto_b_id = self.producto_b.id
            self.cliente_id = self.cliente.id

    def _login_cliente(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = self.cliente_id
            session["_fresh"] = True

    def test_endpoints_cliente_devuelven_datos(self):
        with self.app.app_context():
            compra1 = Compra(
                producto_id=self.producto_a_id,
                usuario_id=self.cliente_id,
                cantidad=1,
                precio_unitario=50.0,
                proveedor_id=self.proveedor_id,
                total=50.0,
                estado="Completado",
                fecha=datetime(2024, 1, 15, tzinfo=timezone.utc),
            )
            compra2 = Compra(
                producto_id=self.producto_b_id,
                usuario_id=self.cliente_id,
                cantidad=2,
                precio_unitario=70.0,
                proveedor_id=self.proveedor_id,
                total=140.0,
                estado="Pendiente",
                fecha=datetime(2024, 2, 10, tzinfo=timezone.utc),
            )
            db.session.add_all([compra1, compra2])
            db.session.commit()

        self._login_cliente()

        resp_tiempo = self.client.get("/data/cliente/compras_tiempo?interval=mes")
        self.assertEqual(resp_tiempo.status_code, 200)
        data_tiempo = resp_tiempo.get_json()
        self.assertTrue(data_tiempo["periodos"])
        self.assertTrue(data_tiempo["totales"])

        resp_favoritos = self.client.get("/data/cliente/productos_favoritos")
        self.assertEqual(resp_favoritos.status_code, 200)
        data_favoritos = resp_favoritos.get_json()
        self.assertIn("CPU-A", data_favoritos["productos"])

        resp_estados = self.client.get("/data/cliente/estados_pedido")
        self.assertEqual(resp_estados.status_code, 200)
        data_estados = resp_estados.get_json()
        self.assertIn("Pendiente", data_estados["estados"])

    def test_intervalo_invalido_regresa_error(self):
        self._login_cliente()
        resp = self.client.get("/data/cliente/compras_tiempo?interval=foo")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())


class DataEndpointsTest(BaseTestCase):
    def _crear_admin(self):
        admin = Usuario(
            nombre="Admin",
            usuario="admin1",
            direccion="Oficina",
            contrasenya="Segura123!",
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
                contrasenya="Segura123!",
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
                    contrasenya="Segura123!",
                    rol="cliente",
                    fecha_registro=datetime(2024, 1, 10),
                ),
                Usuario(
                    nombre="Dos",
                    usuario="u2",
                    direccion="Calle 2",
                    contrasenya="Segura123!",
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

    def test_ventas_totales_rechaza_intervalo_invalido(self):
        with self.app.app_context():
            admin = self._crear_admin()
            self._login(admin.id)

        resp = self.client.get("/data/ventas_totales?interval=foo")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_ventas_totales_trimestre(self):
        with self.app.app_context():
            admin = self._crear_admin()
            cliente = Usuario(
                nombre="Cliente",
                usuario="cli1",
                direccion="Calle 1",
                contrasenya="Segura123!",
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


class ProveedorAjaxTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        with self.app.app_context():
            admin = Usuario(
                nombre="Admin Ajax",
                usuario="admin_ajax",
                direccion="Oficina",
                contrasenya="Segura123!",
                rol="admin",
            )
            proveedor = Proveedor(
                nombre="Proveedor Ajax",
                telefono="999999999",
                direccion="Dir Ajax",
                email="prov_ajax@example.com",
                cif="AJX123456",
                tasa_de_descuento=5.0,
                iva=21.0,
                tipo_producto="Ordenador",
            )
            db.session.add_all([admin, proveedor])
            db.session.commit()
            self.admin_id = admin.id
            self.proveedor_id = proveedor.id

    def _login_admin(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = self.admin_id
            session["_fresh"] = True

    def test_tipos_producto_requiere_autenticacion(self):
        resp = self.client.get(f"/tipos-producto/{self.proveedor_id}", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers.get("Location", ""))

    def test_get_marcas_requiere_autenticacion(self):
        resp = self.client.get("/get_marcas?tipo_producto=Procesador", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_admin_puede_consumir_endpoints_y_editar_productos(self):
        self._login_admin()
        resp_tipos = self.client.get(f"/tipos-producto/{self.proveedor_id}")
        self.assertEqual(resp_tipos.status_code, 200)
        self.assertIn("tipos_producto", resp_tipos.get_json())

        resp_marcas = self.client.get("/get_marcas?tipo_producto=Procesador")
        self.assertEqual(resp_marcas.status_code, 200)
        self.assertTrue(resp_marcas.get_json())

        payload = [
            ("nombre", "Proveedor Ajax"),
            ("telefono", "999999999"),
            ("direccion", "Dir Ajax"),
            ("email", "prov_ajax@example.com"),
            ("cif", "AJX123456"),
            ("tasa_de_descuento", "5"),
            ("iva", "21"),
            ("productos", "Ordenador"),
            ("productos", "Procesador"),
        ]
        resp_edit = self.client.post(
            f"/editar_proveedor/{self.proveedor_id}",
            data=MultiDict(payload),
            follow_redirects=False,
        )
        self.assertEqual(resp_edit.status_code, 302)

        with self.app.app_context():
            proveedor = db.session.get(Proveedor, self.proveedor_id)
            self.assertEqual(proveedor.tipo_producto, "Ordenador, Procesador")

    def test_editar_proveedor_rechaza_productos_fuera_de_catalogo(self):
        self._login_admin()
        payload = [
            ("nombre", "Proveedor Ajax"),
            ("telefono", "999999999"),
            ("direccion", "Dir Ajax"),
            ("email", "prov_ajax@example.com"),
            ("cif", "AJX123456"),
            ("tasa_de_descuento", "5"),
            ("iva", "21"),
            ("productos", "Ordenador"),
            ("productos", "Invalido"),
        ]
        resp_edit = self.client.post(
            f"/editar_proveedor/{self.proveedor_id}",
            data=MultiDict(payload),
            follow_redirects=False,
        )
        self.assertEqual(resp_edit.status_code, 200)

        with self.app.app_context():
            proveedor = db.session.get(Proveedor, self.proveedor_id)
            self.assertEqual(proveedor.tipo_producto, "Ordenador")


class ReportesCacheTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        with self.app.app_context():
            admin = Usuario(
                nombre="Admin Reportes",
                usuario=f"admin_reportes_{secrets.token_hex(2)}",
                direccion="Oficina",
                contrasenya="Segura123!",
                rol="admin",
            )
            db.session.add(admin)
            db.session.commit()
            self.admin_id = admin.id
        self.cache_file = Path(self.app.instance_path) / "report_cache_test.json"
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.app.config["REPORT_CACHE_FILE"] = str(self.cache_file)
        self.cache_history_file = Path(self.app.instance_path) / "cache_history_test.json"
        if self.cache_history_file.exists():
            self.cache_history_file.unlink()
        self.cache_history_file.parent.mkdir(parents=True, exist_ok=True)
        self.app.config["REPORT_CACHE_HISTORY_FILE"] = str(self.cache_history_file)
        self.cache_archive_dir = Path(self.app.instance_path) / "cache_history_archive_test"
        if self.cache_archive_dir.exists():
            for file in self.cache_archive_dir.glob("*"):
                file.unlink()
            self.cache_archive_dir.rmdir()
        self.app.config["REPORT_CACHE_HISTORY_ARCHIVE_DIR"] = str(self.cache_archive_dir)
        self.app.config["REPORT_CACHE_HISTORY_MAX_BYTES"] = 1024
        with self.app.app_context():
            from app.blueprints import reportes

            reportes._CACHE.clear()
            reportes._CACHE_STATS["hits"] = 0
            reportes._CACHE_STATS["misses"] = 0
            assert str(reportes._get_cache_history_file()) == str(self.cache_history_file)
            assert str(reportes._get_cache_history_archive_dir()) == str(self.cache_archive_dir)

    def _login_admin(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = self.admin_id
            session["_fresh"] = True

    def tearDown(self):
        if self.cache_file.exists():
            self.cache_file.unlink()
        if self.cache_history_file.exists():
            self.cache_history_file.unlink()
        if self.cache_archive_dir.exists():
            for file in self.cache_archive_dir.glob("*"):
                file.unlink()
            self.cache_archive_dir.rmdir()
        super().tearDown()

    def test_cache_stats_requiere_autenticacion(self):
        resp = self.client.get("/data/cache_stats", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_admin_puede_actualizar_ttl(self):
        self._login_admin()
        resp = self.client.post("/data/cache_ttl", json={"ttl_seconds": 90})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["ttl_seconds"], 90)
        self.assertTrue(self.cache_file.exists())
        data = json.loads(self.cache_file.read_text(encoding="utf-8"))
        self.assertEqual(data["ttl_seconds"], 90)

        stats = self.client.get("/data/cache_stats")
        self.assertEqual(stats.get_json()["ttl_seconds"], 90)
        history = self.client.get("/data/cache_history")
        events = history.get_json()["events"]
        self.assertTrue(any(evt["type"] == "ttl_update" for evt in events))

    def test_rechaza_ttl_invalidos(self):
        self._login_admin()
        resp = self.client.post("/data/cache_ttl", json={"ttl_seconds": 2})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_cache_history_registra_hits_y_misses(self):
        self._login_admin()
        # Primer consumo genera miss.
        miss_resp = self.client.get("/data/distribucion_productos")
        self.assertEqual(miss_resp.status_code, 200)
        # Segundo consumo debería ser hit gracias a la caché.
        hit_resp = self.client.get("/data/distribucion_productos")
        self.assertEqual(hit_resp.status_code, 200)

        history = self.client.get("/data/cache_history")
        events = history.get_json()["events"]
        types = [evt["type"] for evt in events]
        self.assertIn("miss", types)
        self.assertIn("hit", types)

    def test_chart_export_descarga_archivo(self):
        self._login_admin()
        self.client.get("/data/distribucion_productos")
        resp = self.client.get("/data/chart_export/distribucion_productos")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "text/csv")
        self.assertIn("tipo_producto", resp.get_data(as_text=True))

    def test_historial_rotado_generar_archivo(self):
        self._login_admin()
        self.app.config["REPORT_CACHE_HISTORY_MAX_BYTES"] = 1
        for _ in range(5):
            self.client.get("/data/distribucion_productos")
        self.client.post("/data/cache_ttl", json={"ttl_seconds": 90})
        with self.app.app_context():
            from app.blueprints import reportes

            reportes._rotate_cache_history_if_needed()
        self.assertTrue(self.cache_archive_dir.exists())
        self.assertTrue(list(self.cache_archive_dir.glob("cache_history_*.json")))
        resp = self.client.get("/data/cache_history/export?include_archives=1")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.get_data(as_text=True))
        self.assertTrue(data["events"])

    def test_cache_history_export_descarga_archivo(self):
        self._login_admin()
        self.client.get("/data/distribucion_productos")
        resp = self.client.get("/data/cache_history/export")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "application/json")
        payload = json.loads(resp.data.decode("utf-8"))
        self.assertTrue(payload["events"])
        self.assertTrue(self.cache_history_file.exists())


class ContabilidadFlowsTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        with self.app.app_context():
            admin = Usuario(
                nombre="Admin Conta",
                usuario="admin_conta",
                direccion="Oficina",
                contrasenya="Segura123!",
                rol="admin",
            )
            db.session.add(admin)
            inicializar_plan_cuentas()
            db.session.commit()
            self.admin_id = admin.id

    def _login_admin(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = self.admin_id
            session["_fresh"] = True

    def test_nuevo_asiento_manual_persiste(self):
        self._login_admin()
        payload = MultiDict(
            {
                "descripcion": "Asiento manual test",
                "fecha": "2024-01-02",
                "apuntes-0-cuenta_codigo": "570",
                "apuntes-0-debe": "100",
                "apuntes-0-haber": "0",
                "apuntes-1-cuenta_codigo": "700",
                "apuntes-1-debe": "0",
                "apuntes-1-haber": "100",
            }
        )
        resp = self.client.post("/contabilidad/nuevo-asiento", data=payload, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        with self.app.app_context():
            db.session.remove()
            self.assertEqual(Asiento.query.count(), 1)
            asiento = Asiento.query.first()
            self.assertEqual(len(asiento.apuntes), 2)

    def test_exportar_cuenta_resultados_csv(self):
        with self.app.app_context():
            crear_asiento(
                descripcion="Venta test",
                usuario_id=self.admin_id,
                apuntes_data=[
                    {"cuenta_codigo": "570", "debe": 50, "haber": 0},
                    {"cuenta_codigo": "700", "debe": 0, "haber": 50},
                ],
            )
            crear_asiento(
                descripcion="Costo test",
                usuario_id=self.admin_id,
                apuntes_data=[
                    {"cuenta_codigo": "600", "debe": 30, "haber": 0},
                    {"cuenta_codigo": "300", "debe": 0, "haber": 30},
                ],
            )
            db.session.commit()

        self._login_admin()
        resp = self.client.get("/contabilidad/cuenta-resultados/exportar")
        self.assertEqual(resp.status_code, 200)
        csv_text = resp.data.decode("utf-8")
        self.assertIn("Total Ingresos", csv_text)
        self.assertIn("Total Gastos", csv_text)
        self.assertIn("RESULTADO NETO", csv_text)
        self.assertIn("700", csv_text)
        self.assertIn("600", csv_text)


class CsrfProtectionTest(unittest.TestCase):
    """Ejercita flujos reales con CSRF activo para garantizar que no haya atajos inseguros."""

    def setUp(self):
        self.prev_db = os.environ.get("DATABASE_URI")
        self.prev_csrf = os.environ.get("WTF_CSRF_ENABLED")
        os.environ["DATABASE_URI"] = "sqlite:///:memory:"
        os.environ["WTF_CSRF_ENABLED"] = "true"
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            self.admin = Usuario(
                nombre="Admin CSRF",
                usuario="admin_csrf",
                direccion="Oficina",
                contrasenya="Segura123!",
                rol="admin",
            )
            self.cliente = Usuario(
                nombre="Cliente CSRF",
                usuario="cliente_csrf",
                direccion="Calle 2",
                contrasenya="Segura123!",
                rol="cliente",
            )
            proveedor = Proveedor(
                nombre="Prov CSRF",
                telefono="123456789",
                direccion="Ruta",
                email="prov@ej.com",
                cif="Z1234567X",
                tasa_de_descuento=0,
                iva=21.0,
                tipo_producto="Procesador",
            )
            db.session.add_all([self.admin, self.cliente, proveedor])
            db.session.flush()
            producto = Producto(
                proveedor_id=proveedor.id,
                tipo_producto="Procesador",
                modelo="CSRF-1",
                descripcion="",
                cantidad=5,
                cantidad_minima=0,
                precio=10.0,
                marca="Marca",
                num_referencia="CSRF-1",
            )
            db.session.add(producto)
            db.session.commit()
            self.admin_id = self.admin.id
            self.cliente_id = self.cliente.id
            self.proveedor_id = proveedor.id
            self.producto_id = producto.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        if self.prev_db is not None:
            os.environ["DATABASE_URI"] = self.prev_db
        if self.prev_csrf is not None:
            os.environ["WTF_CSRF_ENABLED"] = self.prev_csrf

    def _login_as(self, user_id):
        with self.client.session_transaction() as session:
            session["_user_id"] = user_id
            session["_fresh"] = True

    def test_eliminar_producto_exige_token_csrf(self):
        self._login_as(self.admin_id)
        resp = self.client.post(f"/eliminar_producto/{self.producto_id}", follow_redirects=False)
        self.assertEqual(resp.status_code, 400)

    def test_cliente_no_puede_editar_proveedor(self):
        self._login_as(self.cliente_id)
        resp = self.client.get(f"/editar_proveedor/{self.proveedor_id}", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/", resp.headers.get("Location", ""))


class PerfilClienteTest(BaseTestCase):
    def test_actualizar_perfil_cliente(self):
        with self.app.app_context():
            cliente = Usuario(
                nombre="Cliente", usuario="cliente_mod", direccion="Calle 1", contrasenya="Segura123!", rol="cliente"
            )
            db.session.add(cliente)
            db.session.commit()

        self.client.post("/login", data={"usuario": "cliente_mod", "contrasenya": "Segura123!"}, follow_redirects=True)
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
