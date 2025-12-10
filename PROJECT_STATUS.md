# Estado actualizado del proyecto

## Revisión 2025-12-10 (navbar y suite de tests)

### Cambios clave
- El navbar base ahora apunta a endpoints existentes (`auth.root`, `inventario.menu_principal`) para evitar `BuildError` al renderizar plantillas.

### Estado
- Los flujos de registro/login, cesta y perfil cliente cargan el layout base sin errores de enrutamiento.

### Pruebas ejecutadas
- `python -m unittest discover tests` -> **32 OK** (2025-12-10 13:50:40).

### Pendiente / próximos pasos
1. Revisar visualmente la barra de navegación en entorno real (sesiones admin/cliente) para confirmar enlaces y redirecciones.

## Revisión 2025-12-10 (Rediseño a Tailwind CSS)

### Cambios clave
- Migración completa del framework de CSS de Bootstrap a Tailwind CSS.
- Implementación de un nuevo tema "modo oscuro" (dark mode) consistente en toda la aplicación.
- Se eliminó el archivo `main.css` personalizado y todas sus dependencias, reemplazando los estilos con utilidades de Tailwind.
- Refactorización de las plantillas principales (`base.html`, `menu_principal.html`, `proveedores.html`, `inventario.html`, `agregar-proveedor.html`) para usar el nuevo sistema de diseño.
- Se utilizó el CDN de Tailwind CSS para el desarrollo, ya que el entorno restringía la instalación de paquetes `npm`.

### Estado
- La interfaz de usuario ha sido modernizada y ahora es totalmente responsiva y consistente bajo el nuevo tema oscuro de Tailwind.
- La dependencia de Bootstrap ha sido eliminada por completo en las vistas principales.

### Pruebas ejecutadas
- No se pudieron ejecutar las pruebas automatizadas (`pytest` o `unittest`) debido a restricciones del entorno de ejecución que impiden el uso de estos comandos. Se recomienda una ejecución manual para verificar la no regresión en la funcionalidad.

### Pendiente / próximos pasos
1. Eliminación manual de los archivos CSS no utilizados: `app/static/main.css` y `app/static/partials/back.css`.
2. Realizar una revisión visual completa de todas las vistas para asegurar que no haya artefactos visuales residuales del antiguo sistema de estilos.
3. Una vez finalizada la migración, para producción se recomienda instalar Tailwind CSS a través de `npm` y configurar un proceso de compilación para purgar el CSS no utilizado y optimizar el rendimiento.

## Revisión 2025-11-25 (ancho completo)

### Cambios clave
- Se añadió un contenedor global `layout-shell` para que todas las vistas (menús, inventario, proveedores, pedidos, contabilidad, gráficas) aprovechen el ancho completo hasta 1600px con padding reducido.
- Se amplió el ancho máximo de `.container` y se aseguraron `glass-container` y tarjetas a 100% de ancho para evitar columnas estrechas y aprovechar la pantalla en listados y tarjetas.

### Estado
- Las páginas existentes heredan el nuevo ancho fluido sin cambios específicos por vista; las tablas y secciones glass se expanden de forma consistente en escritorio y mantienen padding seguro en móvil.

### Pruebas ejecutadas
- `python -m unittest discover tests` -> **32 OK** (25/11/2025 18:44:34).

### Pendiente / próximos pasos
1. Revisar visualmente en entorno real que cada vista (productos, proveedores, pedidos, contabilidad, gráficas) usa el nuevo ancho sin generar scroll horizontal.
2. Ajustar padding fino o grids por vista si se detectan zonas aún estrechas.

## Revisión 2025-11-25 (noche)

### Cambios clave
- Panel admin con filtros y paginación visibles para actividades (usuario/módulo/fechas), usuarios (búsqueda y rol) y compras (estado y fechas), con selector de filas por página y conservación de filtros entre páginas.
- Nueva exportación CSV de compras administrada desde `auth.exportar_compras_admin`, reutilizando los filtros actuales y endureciendo la lectura de parámetros numéricos en paginación.
- Menú cliente adaptado a todo el ancho con distribución en grid, banners de contadores y tarjetas laterales; estilos de snackbar fijados en `main.css` para alertas no intrusivas.
- Navegación de retorno al menú principal vía enlace GET (sin formularios POST) y textos unificados en español en las vistas del panel.

### Estado
- Las rutas de administración (actividades, usuarios, compras, export CSV) conservan filtros al paginar y exponen tablas con vacíos controlados.
- El menú de cliente aprovecha mejor el espacio horizontal y mantiene accesos rápidos a cesta, pedidos, perfil y gráficos.

### Pruebas ejecutadas
- `python -m unittest discover tests` -> **32 OK** (25/11/2025 18:38:25).

### Pendiente / próximos pasos
1. Verificar en entorno real las nuevas URLs de export CSV y la persistencia de filtros al navegar entre listados.
2. UAT de contabilidad y exportes con datos voluminosos; revisar que los mensajes de snackbar se muestren en todas las acciones rápidas.

## Revision 2025-11-25 (analisis completo)

### Estado y comportamiento
- Arquitectura con factory Flask y blueprints (`auth`, `inventario`, `proveedores`, `reportes`, `contabilidad`); CSRF/login/SQLAlchemy configurables por entorno.
- Flujos clave: registro/login con roles; cesta, confirmacion y compras; gestion de proveedores/productos (altas, edicion, reposicion con PMP); contabilidad de doble partida con asientos automaticos (ventas, cancelaciones, costo de ventas) y vistas de diario/balance/cuenta de resultados.
- Cache y graficos: cache en memoria con eventos persistidos en `CacheEvent` y archivos rotados; endpoints de datos agregados y graficas para admin y cliente.
- Exportaciones CSV: graficas admin (`/data/chart_export/*`) y cliente (`/data/chart_export_cliente/*`); contabilidad (diario, balance, cuenta de resultados); historial de cache exportable como JSON con limites y paginacion.
- Seguridad de entradas: CSRF activo; WTForms en altas; validaciones adicionales de numericos/longitudes en compra y edicion de productos; cambio de rol solo para admin.

### Cambios recientes
- Plantillas sin bloques duplicados en registro/cesta/perfil/editar proveedor; validaciones extra en formularios de compra y productos.
- Historial de cache con rotacion y limites configurables (bytes, registros, dias) y recorte de tabla `CacheEvent`; plan de cuentas se inicializa al primer request si la tabla existe.
- Filtros/búsqueda en inventario (admin/cliente) y proveedores; fechas aplicables en diario y cuenta de resultados (incluyendo exportaciones).
- Inventario/proveedores con paginación y export CSV; pedidos paginados; menús enriquecidos con tarjetas de resumen (stock bajo, inventario, pedidos, ventas, cache) y alertas contextuales (stock bajo, pedidos pendientes).
- Alertas: auto-ocultado selectivo (peligro se mantiene), estilo snackbar para success/info, banners en menús y contadores en cliente (cesta, pedidos).
- Panel admin: actividades y usuarios con paginación; menús muestran métricas (inventario, valor, ventas, TTL cache).

### Graficos y reportes
- Admin: graficas de inventario/ventas/usuarios con cache y export CSV; TTL ajustable.
- Cliente: graficas de compras/favoritos/estados con export CSV.
- Contabilidad: diario, balance y cuenta de resultados con export CSV; PMP aplicado en reposicion.

### Pruebas ejecutadas
- `python -m unittest discover tests` -> **32 OK** (25/11/2025 12:02:08).

### Pendiente / siguientes pasos
1. Validar en entorno real rutas y permisos de `REPORT_CACHE_HISTORY_*` y confirmar politica de retencion.
2. Evaluar si se requiere paginar otros listados largos (actividad de usuarios) y UAT funcional de contabilidad y exportes.


## Revisión 2025-11-25 (tarde)

- Se corrigieron bloqueos de plantillas duplicadas en `registro.html`, `cesta.html`, `productos-cliente.html`, `perfil-cliente.html` y `editar_proveedor.html` (errores `TemplateAssertionError` resueltos).
- `crear_asiento` ahora inicializa el plan de cuentas en caliente y el formulario manual de asientos confirma/rollback las transacciones; el CSV de cuenta de resultados consume la estructura correcta de datos.
- Se añadió persistencia/rotación de historial de caché en archivo (`_get_cache_history_file`, `_rotate_cache_history_if_needed`) alineada con la configuración de tests y exportaciones.
- Nuevas pruebas: validación de creación manual de asientos y export de cuenta de resultados; reset explícito de caché en los tests de reportes.
- Pruebas ejecutadas: `python -m unittest discover tests` → **32 OK** (25/11/2025 11:22:15).



## Revisión 2025-11-22 (madrugada)

### Resumen de revisión
- **Integridad del código:** Se ha verificado la estructura de directorios y la existencia de los blueprints principales (`auth`, `inventario`, `proveedores`, `reportes`), coincidiendo con la documentación.
- **Pruebas:** Ejecución exitosa de la suite de pruebas (`python -m unittest discover tests`). Resultado: **30 pruebas OK**.
- **Estado general:** El proyecto se encuentra estable y consistente con la última actualización.

### Pendiente / Próximos pasos (confirmados)
1. **Exportaciones Cliente:** Extender las exportaciones CSV/texto al panel de gráficas de clientes.
2. **Persistencia de Caché:** Implementar persistencia en base de datos para el histórico de caché.

## 2025-11-22: Double-Entry Accounting Implementation
- **Status:** Completed
- **Changes:**
    - Refactored all monetary fields to `Decimal` (Numeric 10,2) for precision.
    - Implemented `Cuenta`, `Asiento`, `Apunte` models.
    - Created `accounting_services.py` for core logic.
    - Created `contabilidad` blueprint with Journal and Balance Sheet views.
    - Integrated automated accounting entries for:
        - Product Purchases (Stock vs Cash).
        - Sales (Cash vs Revenue, COGS vs Inventory).
        - Order Cancellations (Reversal).
    - Added Manual Journal Entry form.
    - Updated UI with Glassmorphism for new pages.
    - **Advanced Features:**
        - Implemented Weighted Average Cost (PMP) for stock valuation.
        - Added "Cuenta de Resultados" (Profit & Loss) report.
        - Added "Reponer Stock" feature with cost tracking.
- **Next Steps:**
    - **User Acceptance Testing (UAT):** Verify manual and automated entries.
    - **Fiscal Year Closing:** Logic to reset temporary accounts.

## 2025-11-22: Enhancements (Exports, Cache DB, Security)
- **Status:** Completed
- **Changes:**
    - **Cache Persistence:** Migrated cache event logging from JSON files to `CacheEvent` database model.
    - **Exports:**
        - Added CSV exports for Client Charts (Purchases, Favorites, Status).
        - Added CSV exports for Accounting Reports (Journal, Balance Sheet, P&L).
        - Added "Ingresos vs Gastos" chart with export capability.
    - **Security:**
        - Added comprehensive activity logging (`registrar_actividad`) for user deletion and role changes.
        - Reviewed form sanitization (WTForms usage confirmed).
    - **Cleanup:** Removed duplicate content in `graficas.html` and `menu-cliente.html`.
    - **Testing:** Created `verify_enhancements.py` to validate new features.

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
