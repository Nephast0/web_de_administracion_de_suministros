# Estado actualizado del proyecto

Este resumen refleja el estado lógico actual después de las últimas refactorizaciones y señala riesgos pendientes más allá de las funciones de gráficos que ya sabemos que requieren corrección.

## Puntos fuertes actuales
- **Factory y blueprints separados:** la aplicación se crea leyendo variables de entorno, mantiene CSRF activo y ahora registra los blueprints `auth`, `inventario`, `proveedores` y `reportes`, reduciendo el acoplamiento del antiguo monolito. 【F:app/__init__.py†L9-L78】【F:app/blueprints/__init__.py†L1-L22】
- **Plantillas migradas a layout base:** las vistas de inventario, compras, mantenimiento, menús y reportes extienden `base.html`, reduciendo duplicidad de cabeceras y asegurando tokens CSRF homogéneos. 【F:app/templates/pedidos.html†L1-L66】【F:app/templates/menu-cliente.html†L1-L39】【F:app/templates/graficas.html†L1-L113】【F:app/templates/productos.html†L1-L111】
- **Modelos y formularios alineados:** las tablas de `Usuario`, `Proveedor` y `Producto` aplican longitudes/unicidad coherentes y ahora usan relaciones explícitas sin warnings de overlaps; los formularios mantienen las mismas restricciones. 【F:app/models.py†L17-L170】【F:app/forms.py†L1-L128】
- **Consultas compatibles con SQLAlchemy 2.x:** las rutas administrativas y de inventario usan `db.session.get`/`abort` en lugar de la API legacy `Query.get`, eliminando warnings y manteniendo trazabilidad de errores. 【F:app/blueprints/auth.py†L150-L193】【F:app/blueprints/inventario.py†L70-L169】【F:app/blueprints/proveedores.py†L185-L227】
- **Flujos críticos y casos negativos cubiertos por tests:** las pruebas incluyen registro/login, compras, métricas, CRUD administrativo (edición/eliminación) y perfil de cliente con SQLite en memoria. 【F:tests/test_flows.py†L1-L410】

## Riesgos y deudas pendientes
- **Plantillas aún heterogéneas:** la vista de gráficas de cliente sigue siendo un stub sin datos y requiere completar la lógica de métricas dedicadas.
- **Cobertura pendiente en flujos de edición/eliminación:** los tests nuevos ejercitan CRUD feliz; falta validar errores de permisos/validaciones bajo CSRF real.
- **Gráficas y métricas:** persiste el riesgo en funciones de gráficos ya identificadas previamente (sin cambios en esta iteración).

## Próximos pasos sugeridos
1. Completar las métricas específicas para clientes y suplantar el stub actual de gráficas.
2. Extender las pruebas a casos de error/permiso en ediciones y eliminaciones con CSRF activo.
3. Revisar las vistas de gráficas rotas para completar la cobertura de reportes antes de nuevos despliegues.
