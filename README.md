# Administración de Suministros

Breve guía para ejecutar la aplicación y mantener la base de datos de forma segura.

## Configuración rápida
- Crea un entorno virtual y ejecuta `pip install -r requirements.txt`.
- Variables clave:
  - `DATABASE_URI`: cadena de conexión SQLAlchemy (por defecto SQLite en `instance/administracion.db`).
  - `SECRET_KEY`: clave para sesiones y CSRF.
  - `SQLALCHEMY_ECHO`: activa logs SQL sólo en desarrollo (`true/false`).
  - `WTF_CSRF_ENABLED`: deja CSRF activo; deshabilítalo sólo en pruebas automatizadas.

## Migraciones con Flask-Migrate
1. Exporta la variable `FLASK_APP=run.py`.
2. Inicializa (una sola vez): `flask db init`.
3. Genera migraciones cuando cambien los modelos: `flask db migrate -m "descripcion"`.
4. Aplica cambios: `flask db upgrade`.

> Se documentan estos pasos para reducir el riesgo de esquemas inconsistentes en despliegues.

## Ejecutar
- Desarrollo: `python run.py` (usa `create_app` con la configuración anterior).
- Tests: `python -m unittest discover tests` (usa SQLite en memoria y desactiva CSRF para flujos automatizados).

## Notas de seguridad
- Mantén `SECRET_KEY` y credenciales fuera del repositorio (variables de entorno).
- Evita activar `SQLALCHEMY_ECHO` en producción para no filtrar consultas ni datos sensibles.

## Arquitectura de rutas
- Las vistas están divididas en blueprints bajo `app/blueprints/` para reducir el monolito original:
  - `auth.py`: login, registro y administración de usuarios/roles.
  - `inventario.py`: menús de admin/cliente, catálogo y flujo de compras.
  - `proveedores.py`: CRUD de proveedores y productos.
  - `reportes.py`: endpoints de métricas y gráficas protegidas por rol.
