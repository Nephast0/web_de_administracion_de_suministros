
import requests
import unittest
from app import create_app, db
from app.models import Usuario, CacheEvent, Compra, Producto, Cuenta, Asiento, Apunte, Proveedor
from datetime import datetime, timezone
import json
import secrets

import os

class TestEnhancements(unittest.TestCase):
    def setUp(self):
        os.environ['DATABASE_URI'] = 'sqlite:///:memory:'
        os.environ['WTF_CSRF_ENABLED'] = 'false'
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.create_test_data()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def create_test_data(self):
        try:
            # Create users
            self.admin_user = Usuario(nombre="Admin", rol="admin", usuario="admin", direccion="Admin Addr", contrasenya="password")
            self.cliente_user = Usuario(nombre="Cliente", rol="cliente", usuario="cliente", direccion="Client Addr", contrasenya="password")
            db.session.add_all([self.admin_user, self.cliente_user])
            db.session.commit()

            # Create Provider
            prov = Proveedor(nombre="Prov Test", telefono="123", direccion="Dir", email="p@t.com", cif="CIF123", tasa_de_descuento=0, iva=21, tipo_producto="General")
            db.session.add(prov)
            db.session.commit()

            # Create product
            prod = Producto(proveedor_id=prov.id, tipo_producto="Tipo A", modelo="Test Prod", descripcion="Desc", cantidad=10, cantidad_minima=5, precio=100, marca="Brand", num_referencia="REF1")
            db.session.add(prod)
            db.session.commit()
            
            # Create purchase
            compra = Compra(usuario_id=self.cliente_user.id, producto_id=prod.id, cantidad=1, precio_unitario=100, proveedor_id=prov.id, total=100, estado="Completado", fecha=datetime.now(timezone.utc))
            db.session.add(compra)
            
            # Create accounting data
            c_ingreso = Cuenta(codigo="700000", nombre="Ventas", tipo="Ingreso")
            c_gasto = Cuenta(codigo="600000", nombre="Compras", tipo="Gasto")
            c_banco = Cuenta(codigo="572000", nombre="Banco", tipo="Activo")
            db.session.add_all([c_ingreso, c_gasto, c_banco])
            db.session.commit()

            asiento = Asiento(descripcion="Venta Test", usuario_id=self.admin_user.id, fecha=datetime.now(timezone.utc))
            db.session.add(asiento)
            db.session.commit()

            ap1 = Apunte(cuenta_id=c_banco.id, debe=121, haber=0)
            ap1.asiento_id = asiento.id
            ap2 = Apunte(cuenta_id=c_ingreso.id, debe=0, haber=121)
            ap2.asiento_id = asiento.id
            db.session.add_all([ap1, ap2])
            
            asiento2 = Asiento(descripcion="Compra Test", usuario_id=self.admin_user.id, fecha=datetime.now(timezone.utc))
            db.session.add(asiento2)
            db.session.commit()
            
            ap3 = Apunte(cuenta_id=c_gasto.id, debe=50, haber=0)
            ap3.asiento_id = asiento2.id
            ap4 = Apunte(cuenta_id=c_banco.id, debe=0, haber=50)
            ap4.asiento_id = asiento2.id
            db.session.add_all([ap3, ap4])
            
            db.session.commit()
        except Exception as e:
            print(f"ERROR IN SETUP: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def login(self, usuario, password):
        return self.client.post('/login', data=dict(usuario=usuario, contrasenya=password), follow_redirects=True)

    def test_cache_persistence(self):
        self.login("admin", "password")
        # Trigger a cache event
        self.client.get('/data/ventas_totales?interval=mes')
        
        with self.app.app_context():
            # Check if event is in DB
            event = CacheEvent.query.first()
            self.assertIsNotNone(event)
            # The event type might be 'miss' or 'hit'
            self.assertTrue(event.event_type in ['miss', 'hit'])

    def test_client_export(self):
        self.login("cliente", "password")
        response = self.client.get('/data/chart_export_cliente/cliente_compras_tiempo?interval=mes')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b"periodo,total", response.data)

    def test_ingresos_gastos_data(self):
        self.login("admin", "password")
        response = self.client.get('/data/ingresos_gastos?interval=mes')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("ingresos", data)
        self.assertIn("gastos", data)
        # We expect some income (121) and expenses (50)
        self.assertTrue(sum(data['ingresos']) > 0)
        self.assertTrue(sum(data['gastos']) > 0)

    def test_ingresos_gastos_export(self):
        self.login("admin", "password")
        response = self.client.get('/data/chart_export/ingresos_gastos?interval=mes')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b"periodo,ingresos,gastos", response.data)

if __name__ == '__main__':
    unittest.main()
