# Estado actualizado del proyecto

Este resumen refleja el estado lógico actual después de las últimas refactorizaciones y señala riesgos pendientes más allá de las funciones de gráficos que ya sabemos que requieren corrección.

## Puntos fuertes actuales
- **Factory y blueprints separados:** la aplicación se crea leyendo variables de entorno, mantiene CSRF activo y ahora registra los blueprints `auth`, `inventario`, `proveedores` y `reportes`, reduciendo el acoplamiento del antiguo monolito. 【F:app/__init__.py†L9-L78】【F:app/blueprints/__init__.py†L1-L22】
- **Plantillas migradas a layout base:** las vistas de inventario, compras, mantenimiento, menús y reportes extienden `base.html`, reduciendo duplicidad de cabeceras y asegurando tokens CSRF homogéneos. 【F:app/templates/pedidos.html†L1-L66】【F:app/templates/menu-cliente.html†L1-L39】【F:app/templates/graficas.html†L1-L113】【F:app/templates/productos.html†L1-L111】
- **Modelos y formularios alineados:** las tablas de `Usuario`, `Proveedor` y `Producto` aplican longitudes/unicidad coherentes y ahora usan relaciones explícitas sin warnings de overlaps; los formularios mantienen las mismas restricciones. 【F:app/models.py†L17-L170】【F:app/forms.py†L1-L128】
- **Consultas compatibles con SQLAlchemy 2.x:** las rutas administrativas y de inventario usan `db.session.get`/`abort` en lugar de la API legacy `Query.get`, eliminando warnings y manteniendo trazabilidad de errores. 【F:app/blueprints/auth.py†L150-L193】【F:app/blueprints/inventario.py†L70-L169】【F:app/blueprints/proveedores.py†L185-L227】
- **Flujos críticos y casos negativos cubiertos por tests:** las pruebas incluyen registro/login, compras, métricas, CRUD administrativo (edición/eliminación) y perfil de cliente con SQLite en memoria. 【F:tests/test_flows.py†L1-L410】
- **Registro endurecido:** el formulario público de alta fuerza el rol 'cliente' y ya no expone la selección manual, evitando auto-asignaciones administrativas. ?F:app/templates/registro.html�L25-L52??F:app/blueprints/auth.py�L59-L87?
- **Tests actualizados:** las pruebas de autenticación ahora validan el rol por defecto y la redirección de clientes tras el login. ?F:tests/test_flows.py?L34-L90?
- **CSRF y permisos cubiertos:** flujos de edición/eliminación fallan sin token y usuarios sin rol son redirigidos; se añadieron pruebas dedicadas. ?F:tests/test_flows.py?L420-L520?
- **Fechas con zona horaria:** los modelos y utilidades usan datetime.now(timezone.utc) para eliminar warnings y mantener consistencia. ?F:app/models.py?L17-L196??F:app/blueprints/helpers.py?L52-L78??F:app/blueprints/reportes.py?L1-L189?
- **Gráficas de cliente completas:** se añadieron endpoints y el frontend de Chart.js con datos reales más pruebas dedicadas. ?F:app/blueprints/reportes.py?L108-L189??F:app/templates/graficas-cliente.html?L1-L123??F:tests/test_flows.py?L250-L330?
- **Cache en reportes:** los endpoints analíticos usan un cache en memoria con TTL configurable para reducir consultas repetidas. ?F:app/blueprints/reportes.py?L1-L220?
- **Alertas de inventario visibles para admins:** el panel de productos recalcula los artículos en umbral mínimo para mostrarlos como aviso. ?F:app/blueprints/inventario.py?L70-L110??F:app/templates/inventario_admin.html?L19-L42?
- **Pruebas de integración de reportes:** la suite ahora valida respuestas de los endpoints de métricas, incluyendo intervalos inválidos y datos de cliente. ?F:tests/test_flows.py?L240-L520?


## Riesgos y deudas pendientes
- **Instrumentación de reportes:** el cache in-memory no tiene métricas ni invalidación automática tras escrituras; falta monitoreo en producción.
- **Cobertura front-end:** las gráficas en Chart.js no cuentan con pruebas automatizadas de interfaz; un cambio en el JS podría pasar desapercibido.
- **Umbrales de alertas configurables:** los avisos de inventario dependen de `cantidad_minima` fija y no se pueden ajustar por rol o categoría.
## Próximos pasos sugeridos
1. Instrumentar métricas/alertas sobre el cache y los tiempos de respuesta de los endpoints analíticos.
2. Añadir pruebas end-to-end (o snapshots JS) para las gráficas tanto de admins como de clientes.
3. Hacer configurables los umbrales/recipientes de las alertas de inventario.

