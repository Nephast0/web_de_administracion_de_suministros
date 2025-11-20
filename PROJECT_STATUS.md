# Estado actualizado del proyecto

## Revisión 2025-11-19 (tarde)

### Cambios realizados
- **Flujos de compra estabilizados:** la ruta de la cesta ahora expone `cesta_items` y el catálogo de clientes ignora productos sin `cantidad_minima`, evitando `UndefinedError` y `TypeError` que bloqueaban el frontend (`app/blueprints/inventario.py`, `app/templates/cesta.html` y `app/templates/productos-cliente.html`). Se añadieron pruebas dedicadas en `CompraFlowTest`.
- **Seguridad en utilidades de proveedores:** los endpoints JSON de tipos, CIF, marcas y modelos ahora requieren autenticación de administrador y cuentan con pruebas de integración (`app/blueprints/proveedores.py`, `tests/test_flows.py::ProveedorAjaxTest`). Además, `editar_proveedor` reaprovecha los checkboxes del alta y retiene los productos seleccionados.
- **UI consistente con el layout base:** `proveedores.html` extiende `base.html`, los botones de navegación son enlaces GET accesibles y el componente de alertas utiliza un botón semántico. Los formularios de "volver" en inventario, cesta, confirmación, etc., dejaron de enviar POST innecesarios.
- **Moneda centralizada e internacionalizada:** el filtro `currency` se apoya en Babel con locale configurable, expone el símbolo a todas las vistas y cuenta con pruebas unitarias (`app/__init__.py`, `tests/test_filters.py`). Los totales dinámicos de la cesta y las gráficas usan `Intl.NumberFormat` para mantener coherencia visual (`app/templates/cesta.html`, `app/templates/graficas.html`).
- **Gráficas accesibles con resúmenes y exportaciones:** los canvas incluyen descripciones `aria`, los tooltips muestran unidades localizadas y cada widget expone resúmenes descargables (TXT) y CSV vía `/data/chart_export/*` (`app/templates/graficas.html`, `app/blueprints/reportes.py`).
- **Caché administrable con histórico persistente/rotado:** el panel muestra hits/misses en tiempo real, permite ajustar el TTL, persiste y rota el histórico (`instance/cache_history.json` + archivos de respaldo) y habilita descargas completas (`app/blueprints/reportes.py`, `app/templates/graficas.html`, `tests/test_flows.py::ReportesCacheTest`).
- **Checkboxes de productos migrados a WTForms:** las altas y ediciones de proveedores ahora usan `MultiCheckboxField`, validaciones server-side y helpers compartidos para consolidar la lista de productos (`app/forms.py`, `app/blueprints/proveedores.py`, `app/templates/agregar-proveedor.html`, `app/templates/editar_proveedor.html`). Se añadió una prueba que asegura que valores fuera de catálogo se rechazan y se declaró la dependencia `email-validator`.

### Estado actual
- La navegación administrativa y de clientes funciona sin errores de templating y con enlaces coherentes.
- Los formularios de proveedor (alta/edición) comparten opciones y mantienen los productos seleccionados, mientras que los endpoints auxiliares ya no filtran datos sin autenticación.
- El diseño mantiene una misma base tipográfica y cromática gracias al uso de `base.html` y al formato de moneda homogéneo en servidor y cliente.
- Los totales monetarios respetan el locale configurado y el panel administrativo expone la salud de la caché junto con un control de TTL en caliente, incluyendo histórico de hits/misses.

### Pruebas ejecutadas
- `python -m unittest discover tests` → 30 pruebas OK (20/11/2025 19:35, con logs esperados del caché y de CSRF).

### Pendiente / próximos pasos
1. Extender las exportaciones CSV/texto al panel de gráficas de clientes y ofrecer enlaces directos desde los endpoints públicos.
2. Persistir el histórico de caché en base de datos (o en una tabla de auditoría) con políticas de retención configurables y exponer una vista paginada en el panel admin.
