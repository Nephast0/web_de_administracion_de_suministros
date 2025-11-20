# Estado actualizado del proyecto

## Revisión 2025-11-19 (tarde)

### Cambios realizados
- **Flujos de compra estabilizados:** la ruta de la cesta ahora expone `cesta_items` y el catálogo de clientes ignora productos sin `cantidad_minima`, evitando `UndefinedError` y `TypeError` que bloqueaban el frontend (`app/blueprints/inventario.py`, `app/templates/cesta.html` y `app/templates/productos-cliente.html`). Se añadieron pruebas dedicadas en `CompraFlowTest`.
- **Seguridad en utilidades de proveedores:** los endpoints JSON de tipos, CIF, marcas y modelos ahora requieren autenticación de administrador y cuentan con pruebas de integración (`app/blueprints/proveedores.py`, `tests/test_flows.py::ProveedorAjaxTest`). Además, `editar_proveedor` reaprovecha los checkboxes del alta y retiene los productos seleccionados.
- **UI consistente con el layout base:** `proveedores.html` extiende `base.html`, los botones de navegación son enlaces GET accesibles y el componente de alertas utiliza un botón semántico. Los formularios de "volver" en inventario, cesta, confirmación, etc., dejaron de enviar POST innecesarios.
- **Formato de moneda centralizado:** se añadió el filtro `currency` en `app/__init__.py` y se aplicó a todas las tablas que muestran precios o totales (inventario, pedidos, menú admin, confirmaciones, etc.). El script de la cesta conserva el símbolo al recalcular totales.
- **Checkboxes de productos migrados a WTForms:** las altas y ediciones de proveedores ahora usan `MultiCheckboxField`, validaciones server-side y helpers compartidos para consolidar la lista de productos (`app/forms.py`, `app/blueprints/proveedores.py`, `app/templates/agregar-proveedor.html`, `app/templates/editar_proveedor.html`). Se añadió una prueba que asegura que valores fuera de catálogo se rechazan y se declaró la dependencia `email-validator`.
- **Moneda con i18n real y caché administrable:** el filtro `currency` ahora se apoya en Babel con locale configurable, expone el símbolo a las plantillas y cuenta con pruebas unitarias (`app/__init__.py`, `tests/test_filters.py`). El panel de gráficas muestra hits/misses del caché en tiempo real y permite ajustar el TTL desde la interfaz (`app/templates/graficas.html`, `app/blueprints/reportes.py`, `tests/test_flows.py::ReportesCacheTest`).
- **Formato localizado también en JS + TTL persistente:** los totales dinámicos de la cesta y las gráficas usan `Intl.NumberFormat` con el locale configurado (`app/templates/cesta.html`, `app/templates/graficas.html`). El TTL del caché se persiste en `instance/report_cache.json`, se recarga al iniciar y se expone un histórico de eventos/hits (`app/blueprints/reportes.py`, `tests/test_flows.py`).

### Estado actual
- La navegación administrativa y de clientes funciona sin errores templating y con enlaces coherentes.
- Los formularios de proveedor (alta/edición) comparten opciones y mantienen los productos seleccionados, mientras que los endpoints auxiliares ya no filtran datos sin autenticación.
- El diseño mantiene una misma base tipográfica y cromática gracias al uso de `base.html` y al formato de moneda homogéneo.
- Las validaciones de proveedores se realizan enteramente vía WTForms, reutilizando la misma selección de productos tanto en alta como en edición dentro del blueprint.
- Los totales monetarios respetan el locale configurado y el panel administrativo expone la salud de la caché junto con un control de TTL en caliente.
- El TTL configurado sobrevive reinicios gracias al archivo de configuración persistente y el histórico de caché permite auditar hits/misses recientes desde la UI/admin.

### Pruebas ejecutadas
- `python -m unittest discover tests` -> 27 pruebas OK (20/11/2025 14:26, con logs esperados del caché y de CSRF).

### Pendiente / próximos pasos
1. Sincronizar las etiquetas numéricas de Chart.js con unidades dinámicas (€, cantidades) y proveer tooltips accesibles para lectores de pantalla.
2. Guardar el histórico de eventos de caché en una tabla o log rotativo para mantener trazabilidad más allá de la sesión actual y permitir exportarlo.
