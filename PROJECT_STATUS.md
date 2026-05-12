# Estado actualizado del proyecto

## Revisión 2026-05-12 (noche) — Rediseño visual "serio" + theme switcher reubicado

### Decisión
A petición de usuario: **rediseño visual completo más sobrio y ejecutivo**. Las 4 paletas anteriores (`elegant`, `cyberpunk`, `corporate`, `emerald`) se descartan en favor de 4 paletas nuevas pensadas para un sistema de gestión empresarial serio. El theme switcher ya no vive en el navbar — se mueve a la pantalla de perfil (sección "Apariencia").

### Nuevos temas (oscuros, ejecutivos)
| Theme | Identidad | Primary | Canvas 900 |
|---|---|---|---|
| **`slate`** (default) | Corporativo serio | Azul cobalto (`#3b82f6`) | Slate puro (`#0f172a`) |
| **`graphite`** | Monocromático severo | Gris claro (`#d4d4d8`) | Zinc puro (`#121214`) |
| **`obsidian`** | Premium ejecutivo | Dorado champagne (`#ca8a04`) | Warm black (`#13100d`) |
| **`sapphire`** | Tech profundo | Cyan (`#06b6d4`) | Navy intenso (`#081626`) |

Los temas legacy se remapean automáticamente al equivalente más cercano en `theme.js::normalize()` (elegant→slate, cyberpunk→sapphire, corporate→slate, emerald→obsidian) para no romper a usuarios con `localStorage.theme` existente.

### Cambios visuales aplicados

#### Tipografía
- **Adiós Playfair Display italic.** Toda la app vive ahora en **Inter** (sans). La jerarquía la dan peso y tracking, no la familia.
- En `@layer base` se definen pesos por nivel: h1 `font-weight: 300`, h2 `400`, h3 `500`. Tracking apretado (-0.025em → -0.015em).
- Botón "Suministros CNCV" del navbar: pasa de `text-3xl font-bold italic` a `text-xl font-semibold tracking-tight`.

#### Componentes refinados
- `glass-panel`: `backdrop-blur(8px)` (antes 12px), opacidad `canvas-900/0.6` (antes 800/0.4).
- `glass-card`: hover sin `scale-*`, sólo cambio de border + bg.
- `form-input`: focus ring de 2px (antes 3px) con `0.2` de opacidad (antes 0.25).
- `btn-primary` / `btn-secondary`: ahora `rounded-md` por defecto (no `rounded-full`). Sin shadow neon. `btn-elegant` usa `filter: brightness(1.08)` en vez de `translateY(-1px)`.
- Scrollbar custom de 6px integrado en el design system (antes inline en perfil).

#### Refactor masivo de templates (21 archivos)
- **`font-heading italic` → `font-heading`** (el italic dejaba de tener sentido sin Playfair).
- **`text-transparent bg-clip-text bg-gradient-to-r from-X to-Y` → `text-canvas-100`** (15+ instancias). Los gradientes en texto eran ruido visual.
- **`font-bold` en headings → `font-semibold`** (más sobrio, mejor jerarquía).
- **`text-4xl` en headings → `text-3xl`**; **`text-3xl` → `text-2xl`** (cabeceras más razonables).
- **`tracking-wide` removido** de headings (Inter ya tiene buen tracking nativo).
- **`shadow-2xl` → `shadow-lg`**, **`shadow-primary-*` eliminado** completamente (neon glow fuera).

### Theme switcher movido a `/perfil_cliente`
- Eliminado el dropdown del navbar (`base.html` pasó de ~210 a ~175 líneas).
- Eliminado el script switcher inline.
- Añadida sección "Apariencia" en `perfil-cliente.html` con 4 tarjetas (botones) clicables, cada una con preview gradient del tema.
- El estado activo se resalta dinámicamente (border + bg primary-500/10) via script local con `nonce`.
- Etiqueta "Tema activo: …" que se actualiza al cambiar.

### Endpoint perfil accesible para ambos roles
- Eliminado `@role_required("cliente")` de `inventario.perfil_cliente`.
- El template tiene back-button condicional: admin → `inventario.menu_principal`; cliente → `inventario.menu_cliente`.
- Botón "Ver pedidos" sólo visible para cliente (admin no tiene pedidos personales).
- Icono `account_circle` en el navbar enlaza al perfil para ambos roles.

### Verificación
- **34 tests pasan** (mismo número, sin regresiones funcionales).
- **Preview visual probado**: login se ve sobrio, dashboard admin, perfil con sección apariencia, cambio entre los 4 temas funcional, sapphire muestra borde cyan en la tarjeta activa.
- **CSS rebuild**: limpio, ~50KB minified.

### Métricas
- **Archivos modificados**: 26 (21 templates + `input.css` + `tailwind.config.js` + `theme.js` + `base.html` + `inventario.py` + `DESIGN_SYSTEM.md` + `PROJECT_STATUS.md`).
- **Líneas eliminadas netas**: ~80 (theme switcher inline, gradientes redundantes, italic).
- **Endpoints Flask**: 63 (sin cambio).

### Pendientes
- **Encoding bug preexistente**: el `<select>` de moneda en perfil muestra "EspaÃ±ol" en vez de "Español". Encoding mal interpretado en `forms.py::EditarPerfilForm.currency_locale.choices`. No introducido por este rediseño — heredado del estado anterior. Marcar para sesión futura.
- **A11y completa con paletas nuevas**: contraste en cada tema, focus rings consistentes, navegación por teclado en el theme switcher.

---

## Revisión 2026-05-12 (tarde) — Auditoría post-antigravity + hardening

### Estado actual
- **34 tests pasan**, 0 fallos. Suite estable.
- **0 path collisions** en el `url_map` de Flask (era 1 antes: `/` chocaba entre `auth.root` y `reportes.index`).
- **0 colores Tailwind hardcodeados** en templates (era 1: `text-purple-400`, `text-pink-400` residuales).
- **0 URLs hardcodeadas** en `href`/`action` de templates (eran 2: `/agregar-producto`).
- **0 imports muertos** detectados por análisis AST (eran 3: `Apunte`, `ActividadUsuario`, `case`).
- **0 botones icon-only sin `aria-label`** (eran 8 — incluye mobile nav toggle, acciones de tabla, eliminar línea de asiento).
- **Browserslist DB** actualizado (`caniuse-lite` al día), CSS rebuild limpio sin warnings.
- **Paletas refinadas** (commit `8706f5a` por antigravity): elegant→Velvet Indigo, cyberpunk→Neon Fuchsia, corporate→Trust Blue + Clean Slate, emerald→Fresh Emerald + Forest Zinc.

### Bugs corregidos en esta auditoría

#### Crítico — `getThemeColor()` rompía Chart.js (preexistente)
El helper JS leía las CSS vars como `"128 90 255"` (formato `R G B` sin `rgb()` ni comas — necesario para componer con `rgb(var(--color-X) / alpha)` en Tailwind). Chart.js recibía ese string como color y silenciosamente caía al default. Además, el truco `color + '40'` para añadir alpha solo funcionaba con hex de 6 chars, no con `rgb()`.

**Arreglo** (`graficas.html`, `graficas-cliente.html`):
```js
const getThemeColor      = (v, fb) => raw ? `rgb(${raw.replace(/\s+/g, ', ')})` : fb;
const getThemeColorAlpha = (v, a, fb) => raw ? `rgba(${raw.replace(/\s+/g, ', ')}, ${a})` : fb;
```
+ pre-computación de variantes `secondaryBg`, `dangerBg`, `successSoft`, `infoSoft`, etc. con alpha aplicado correctamente.

#### Path collision: `auth.root` vs `reportes.index` en `/`
Ambos blueprints registraban `/`. Como auth se registraba primero, `reportes.index` era código muerto. Además referenciaba `url_for('main.index')` con un blueprint que no existe → `BuildError` si alguna vez se hubiera ejecutado.
**Arreglo**: eliminada `reportes.index` (código muerto) + limpiados imports muertos `redirect`, `url_for` que dejó. Documentado en comentario sobre por qué falta el endpoint.

#### URLs hardcodeadas
`<form action="/agregar-producto">` y `<a href="/agregar-producto">` en `agregar-producto.html` e `inventario_admin.html` migrados a `{{ url_for('proveedores.agregar_producto') }}`.

#### Colores hardcodeados en gráficos
- `text-purple-400` → `text-primary-400` (`graficas.html`, h3 "Ingresos por Usuario").
- `text-pink-400`   → `text-success-400` (`graficas.html`, h3 "Ingresos vs Gastos").
- 5 colores hex hardcoded del doughnut de `graficas-cliente.html` migrados a los 5 tokens semánticos del DS (`primarySoft`, `secondarySoft`, `dangerSoft`, `successSoft`, `infoSoft`).
- Eliminados `purple`/`pink` de `themeColors` (5-color scheme ahora usa los 5 semánticos del DS).

#### Imports muertos (detectados por análisis AST)
- `contabilidad.py`: `Apunte` (no referenciado).
- `inventario.py`: `ActividadUsuario` (no referenciado).
- `reportes.py`: `case` de SQLAlchemy + `redirect`/`url_for` huérfanos.
- `accounting_services.py`: `datetime` (no referenciado, sólo `func`).

#### Accesibilidad — 8 botones/links icon-only sin `aria-label`
- `base.html`: nav-toggle mobile (`Abrir menú de navegación`).
- `inventario_admin.html`: editar/eliminar producto en filas de tabla.
- `proveedores.html`: editar/eliminar proveedor.
- `menu-admin.html`: buscar actividades + eliminar usuario.
- `contabilidad/nuevo_asiento.html`: eliminar línea del asiento.

### Métricas
- **Archivos modificados**: 11 (`graficas.html`, `graficas-cliente.html`, `agregar-producto.html`, `inventario_admin.html`, `proveedores.html`, `menu-admin.html`, `base.html`, `nuevo_asiento.html`, `reportes.py`, `inventario.py`, `contabilidad.py`, `accounting_services.py`, `DESIGN_SYSTEM.md`, `PROJECT_STATUS.md`).
- **Líneas de código eliminadas**: ~30 (función muerta + imports muertos + colores hex literales sustituidos por tokens).
- **Endpoints Flask totales**: 63 (era 64 con la colisión).

### Pendientes (sin urgencia)
- **a11y completa**: contraste con paletas nuevas (especialmente cyberpunk, el más saturado), navegación por teclado en modal/dropdown, focus rings consistentes.
- **CSP `style-src`**: sigue requiriendo `'unsafe-inline'` por Chart.js. Wrapper o sustitución pendiente.
- **Tabla `proveedor_tipo_producto`**: el modelo `ProveedorTipoProducto` no declara `__tablename__` explícito (usa el default `proveedortipoproducto`). Aceptable pero documentable.

---

## Revisión 2026-05-12 (mañana) — Sprint visual completo (4 sprints + design system)

### Estado actual
- **34 tests pasan** (32 previos + 2 nuevos de regresión para `/contabilidad/balance` y `/contabilidad/diario`).
- **Smoke test end-to-end**: 14/14 URLs admin y anónimas renderizan 200 OK sin BuildError ni jinja sin resolver.
- **Tailwind compilado con npm** (no CDN runtime). Build: `npm run build:css` → `app/static/css/tailwind.css` (~45KB minified).
- **CSP estricta sin `script-src 'unsafe-inline'`** activa: scripts inline usan `nonce="{{ csp_nonce() }}"` generado per-request.
- **Sistema de design documentado** en `DESIGN_SYSTEM.md` (tokens, componentes, patrones, do's/don'ts).

### Cambios ejecutados en esta sesión

#### Sprint 1 — Fixes estructurales
- **5 clases de componente "fantasma" definidas** en CSS (`form-input`, `glass-table`, `glass-card`, `btn-primary`, `btn-secondary`). Antes estaban en uso (161 ocurrencias) pero no definidas en ningún sitio.
- **`<main>` anidado eliminado** en 21 templates (la auditoría original decía 6 — había más). Bonus: corregido un `</main>{% endblock %}` duplicado en `proveedores.html`.
- **`text-decoration-none` (clase Bootstrap inválida en Tailwind) → `no-underline`** — 31 reemplazos en 6 archivos.
- **Logout duplicado eliminado** de `menu-cliente.html`.

#### Sprint 2 — Tokens semánticos
- **4 paletas semánticas nuevas** en `:root` (`success`, `danger`, `warning`, `info`) — 44 vars CSS + 44 mappings Tailwind. Theme-independent (un rojo de error es rojo en los 4 temas).
- **Migración de 123 colores hardcodeados** a tokens semánticos (`emerald-* → success-*`, `red-* → danger-*`, `amber-* → warning-*`, `green-400 → success-400`) en 19 templates.
- **Migración de 142 colores legacy** (`slate-* → canvas-*`, `indigo-* → primary-*`, `rose-* → danger-*`) en 6 templates más.
- **`graficas.html` admin refactorizado**: cierra el pendiente de diciembre 2025. Chart.js ahora lee colores del CSS via `getThemeColor()` con los nuevos tokens semánticos — los gráficos cambian con el tema.
- **Bug del snackbar corregido**: el banner "success" mapeaba a `primary` (color acento) y "info" a `canvas` (gris). Ahora cada categoría usa su token correcto.

#### Sprint 3 — Pulido visual
- **Wrappers consolidados a 3 patrones canónicos** (`default` / `form-centered` / `viewport-centered`). 6 archivos con `my-8 → my-6`; 1 con `pb-12` añadido.
- **Banner de marca duplicado eliminado** en `menu-cliente.html` y `menu_principal.html`. Bonus: corregido conflicto `text-xl text-sm` simultáneos en `menu_principal`.
- **Botón "Volver" auditado**: dos patrones (pill icon-only y inline link) ambos válidos en su contexto. Bonus: migrados 5 residuales `teal-* → primary-*`.
- **Escala canónica de 5 tamaños de icono** aplicada en 19 archivos (72 normalizaciones). Bonus: migrados 3 `blue-* → info-*`.
- **Modal de confirmación reutilizable** (`window.confirmDialog`) y **toast** (`window.showToast`) en `base.html`. API declarativa via `data-confirm="..."` en forms/links. 6 call sites migrados (5 forms con `onsubmit="return confirm(...)"` + 1 archivo con `confirm()`/`alert()` en JS). Erradicados `confirm()` y `alert()` nativos.

#### Auditoría funcional (entre Sprint 3 y 4)
- **Eliminado `inventario.html`** (código muerto: huérfano + 3 `url_for` rotos).
- **Arregladas 9 referencias `url_for('menu.menu_principal')` rotas** (el blueprint se llama `inventario`, no `menu`). 2 en templates (`contabilidad/balance.html`, `contabilidad/diario.html`) + 7 en código Python (`contabilidad.py`) que sólo se activaban cuando un cliente intentaba acceder a URLs admin.
- **Arreglado bug funcional preexistente** en `contabilidad.py::balance`: `totales[c.tipo] += saldos[c.id]` lanzaba `KeyError` si el tipo de cuenta no estaba pre-poblado. Ahora usa `setdefault` defensivo.
- **2 tests de regresión añadidos** (`ContabilidadRenderTest`) que renderizan `/balance` y `/diario` autenticados — evitan que estos `BuildError` vuelvan a pasar inadvertidos.

#### Sprint 4 — Infraestructura
- **npm + Tailwind compilado**: `package.json`, `tailwind.config.js`, `app/static/css/input.css` extraídos de las 95 líneas de config inline + 3 bloques `<style>` que vivían en `base.html`.
- **Safelist Tailwind** para clases generadas dinámicamente desde JS (variantes del modal, variantes del toast).
- **JS externalizado**: `app/static/js/theme.js` (pre-paint, evita flash de tema) + `app/static/js/ui.js` (modal, toast, mobile nav, data-confirm interceptor, theme switcher delegation).
- **Todos los handlers inline migrados a delegated events** (`onclick=`/`onchange=`/`onsubmit=` cero en templates): `data-set-theme`, `data-flash-close`, `data-remove-closest`, `data-auto-submit`, `data-action`.
- **Todos los `style="..."` inline migrados a clases CSS** (`animation-delay-X`), incluyendo el caso dinámico de `balance.html` con interpolación Jinja.
- **CSP nonce** implementado: `app/__init__.py::_generate_csp_nonce` genera nonce per-request, expuesto al template como `csp_nonce()`. Sustituido en `Content-Security-Policy` header en `after_request`. 8 `<script>` inline restantes (Chart.js wrappers, page-specific JS) ahora llevan `nonce="{{ csp_nonce() }}"`.
- **CSP endurecida**: eliminado `script-src 'unsafe-inline'`. Sigue presente `style-src 'unsafe-inline'` por compatibilidad con estilos dinámicos de Chart.js (documentado para revisión futura).
- **`base.html` pasó de 873 líneas → 209 líneas** (76% reducción).

### Métricas
- **Templates tocados al menos una vez**: 25 (todos los del proyecto + eliminado `inventario.html`).
- **Archivos creados nuevos**: 6 — `DESIGN_SYSTEM.md`, `package.json`, `tailwind.config.js`, `app/static/css/input.css`, `app/static/js/theme.js`, `app/static/js/ui.js`.
- **Reducción de `<script>` inline en templates**: 200+ líneas → 0 (todo en archivos `.js` o con nonce).
- **Tests**: 32 → 34 (con 2 de regresión nuevos).

### Próxima fase (sin urgencia, opcional)
- **Endurecer `style-src`**: eliminar `'unsafe-inline'` de style-src requeriría envolver Chart.js para que no inyecte estilos dinámicos, o aceptar perder algunos efectos visuales de los gráficos.
- **CI**: añadir un step que corra `npm run build:css` antes del deploy (o asumir que `tailwind.css` se commitea — actualmente sí lo está).
- **Auditoría a11y completa**: contraste, navegación por teclado, ARIA labels en componentes complejos (modal ya tiene; tablas y dropdowns no fueron auditados a fondo).

---

## Revisión 2026-05-11 (Cierre de auditoría — repo al día, siguiente fase: visual)

### Estado actual
- **Rama `main` al día con `origin/main`** en `2e5a58a` (push hecho el 2026-05-11). No hay commits locales sin publicar ni remotos sin integrar.
- **Working tree limpio.** Los artefactos temporales versionados (`test_output*.txt`, `migration_error.txt`) ya no están en el árbol — los eliminó `e06ca85` al integrarlo. `.gitignore` ya los cubre a futuro.
- **Suite de tests**: `python -m unittest discover tests` → **32 OK** en 10.9 s (entorno local Windows, venv del proyecto).
- **Dev server verificado**: `FLASK_ENV=development venv\Scripts\python.exe run.py` arranca en `http://127.0.0.1:5000`, plan de cuentas inicializado, `GET /` → 200. Configuración guardada en `.claude/launch.json` para `preview_start`.

### Cambios ejecutados en la sesión 2026-05-11
1. **Commit `2e5a58a`** — auditoría + higiene de repo (ver detalle abajo).
2. **`git pull --rebase origin main`** — integrados los 3 commits remotos (`e06ca85`, `f437f47`, `c9705bf`) que limpian temporales y actualizan `.gitignore`.
3. **`git push origin main`** — local y remoto sincronizados.
4. **Suite de tests** corrida en el entorno local: 32 OK.
5. **Dev server** verificado vía `preview_start`.

### Próxima fase (acordada con el usuario): trabajo visual
La parte de aplicación está sana y desbloqueada. La próxima sesión entra en **modificación de la parte visual** (templates Jinja + Tailwind). Pendientes visuales heredados que conviene resolver en esta fase:

- **Refactor `graficas.html` admin** — usar colores semánticos dinámicos en Chart.js, igual que el panel cliente.
- **Compilar Tailwind con npm + purgado** — sustituye el CDN y permite eliminar `'unsafe-inline'` de la CSP. Mejora seguridad real y velocidad de carga.
- **Auditoría de consistencia visual** — los componentes "Elegant Dark" (`glass-panel`, `form-input`, `btn-elegant`, `glass-table`) viven inline en templates, sin tokens centralizados. Candidato a formalizar como mini design system documentado.
- **Limpieza de referencias a CSS obsoletos** — verificar que ningún template apunta a `main.css` o `partials/back.css` (no existe ya la carpeta `app/static/`).
- **Revisión cross-template** — coherencia de navbar, anchos, snackbars, alertas, estados vacíos en todas las vistas admin y cliente.

### Backlog técnico (en segundo plano hasta que avance la fase visual)
- `verify_enhancements.py` — 4 fallos antiguos de fixture; decidir entre arreglar o eliminar si la suite oficial cubre.
- Flask-Limiter + Redis para rate-limit multi-worker (sólo si planifica despliegue real).
- Cierre de ejercicio fiscal en contabilidad (reset de cuentas temporales).
- Persistir histórico de caché en DB con vista paginada (parcialmente hecho con `CacheEvent`).
- UAT funcional de contabilidad y exports con volumen real.

---

## Revisión 2026-05-11 (Auditoría + correcciones de higiene)

### Contexto
Tras cinco meses sin actualización en este documento se hizo una auditoría completa. Detalle en `AUDITORIA_2026-05-11.md`. El código de aplicación está sano y consistente con la revisión de 12-dic-2025 (hardening OWASP). Los problemas principales eran de higiene de repositorio.

### Cambios aplicados en esta revisión
- **`.gitattributes` añadido** con `* text=auto eol=lf` para evitar que el repo entero se marque como modificado por diferencias CRLF↔LF. Binarios y scripts de Windows tratados explícitamente.
- **`auth.registro` ya no loguea contraseñas.** El log de `request.form` ahora pasa por un filtro que omite `contrasenya`, `contrasena`, `password` y `csrf_token`, alineándose con el patrón ya usado en `auth.login`.

### Estado del repositorio (pendientes externos a este commit)
- La rama local estaba **3 commits por detrás** de `origin/main`. Esos commits remotos (`e06ca85`, `f437f47`, `c9705bf`) ya eliminan `test_output*.txt`, `migration_error.txt`, `.idea/*` y actualizan `.gitignore`. **Se recomienda hacer fast-forward antes del próximo desarrollo.**
- 47 archivos aparecían como `modified` por terminadores de línea (CRLF↔LF). El nuevo `.gitattributes` cubre el caso a futuro; falta una renormalización única (ver script `scripts/normalize-git.ps1` o ejecutar `git add --renormalize .` tras el pull).

### Hallazgos secundarios (no aplicados, requieren decisión)
- `verify_enhancements.py` muestra 4 fallos antiguos (`302 != 200`, "event unexpectedly None"). El snapshot es de 22-nov-2025 y el fixture cliente parece haber perdido sesión. Falta re-correr en el entorno actual y, o bien arreglar el fixture, o retirar el script si la suite de `unittest` ya cubre los escenarios.
- Rate-limit de login en memoria (`auth._LOGIN_ATTEMPTS`) no escala a multi-worker — pendiente migrar a Flask-Limiter + Redis cuando se planifique despliegue real.
- Tailwind sigue cargándose por CDN; queda como deuda el build con npm + purgado para eliminar `'unsafe-inline'` de CSP.

### Pruebas ejecutadas
- `python -m unittest discover tests` → recolecta los 32 tests; ejecución completa pendiente en el entorno Windows del usuario (el sandbox Linux marca 7 errores por `PermissionError` en `instance/`, no son fallos de código).

### Próximos pasos (orden sugerido)
1. Ejecutar `scripts/normalize-git.ps1` (incluido en este commit) para traer los 3 commits remotos y normalizar terminadores.
2. Re-correr `verify_enhancements.py` y decidir su futuro.
3. Backlog: Flask-Limiter, Tailwind compilado, cierre de ejercicio contable, persistencia DB del histórico de caché.

---

## Revision 2025-12-12 (Hardening OWASP)

### Cambios clave
- **Configuracion segura:** `create_app` exige `SECRET_KEY` en produccion, endurece cookies (`HttpOnly`, `Secure`, `SameSite=Lax`) y prepara esquema HTTPS por defecto; `run.py` deja de forzar debug y lo toma de `FLASK_DEBUG`.
- **Autenticacion y CSRF:** se elimina logging de credenciales, se limpia la sesion antes de `login_user` para evitar fijacion y `logout` ahora es solo POST; las plantillas `base.html` y `menu-cliente.html` usan formulario POST con CSRF para cerrar sesion.
- **Exportaciones CSV seguras:** helper `write_safe_csv_row` neutraliza payloads tipo formula en todos los CSV (compras admin, productos, proveedores, reportes, contabilidad).
- **Confiabilidad:** `crear_asiento` deja de usar lista mutable por defecto.

### Estado
- Endurecimiento de superficies criticas (OWASP A01/A02/A03/A05/A07/A09) aplicado sin romper rutas existentes.

### Pruebas ejecutadas
- `python -m compileall app`

### Pendiente / proximos pasos
1. Definir `SECRET_KEY` y servir bajo HTTPS en despliegue para que los flags `Secure` se apliquen.
2. Revisar que los proxies/dominios finales preserven encabezados de seguridad (CSP, HSTS) y el rate limiting en producción.

## Revision 2025-12-12 (Cabeceras y rate limiting)

### Cambios clave
- Cabeceras de seguridad globales: CSP por defecto (self + Tailwind CDN + Google Fonts), `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` y HSTS automático si el esquema preferido es HTTPS.
- Limitador de intentos de login por IP (ventana 10 min, 5 intentos), con limpieza tras éxito; mantiene bypass en modo TESTING.

### Pruebas ejecutadas
- `python -m unittest discover tests` -> OK (32 tests).

## Revision 2025-12-12 (Tests actualizados)

### Cambios clave
- Tests ajustados al hardening: los entornos de prueba fijan `FLASK_ENV=testing` y `SECRET_KEY` para pasar las nuevas validaciones de arranque.
- Ruta de `reportes.index` normalizada a `/` para evitar reglas vacías en Flask/Werkzeug.

### Pruebas ejecutadas
- `python -m unittest discover tests` -> OK (32 tests).

### Pendiente / proximos pasos
1. Considerar fixtures con HTTPS y cookies `Secure` simuladas para validar flags de sesión en integraciones end-to-end.

## Revisión 2025-12-10 (Diseño "Elegant Dark" y Mejoras de Flujo)

### Cambios clave
- **Rediseño Completado ("Elegant Dark"):**
    - Se implementó un tema unificado baseado en Tailwind CSS con paleta "Deep Indigo" y "Slate".
    - Tipografía actualizada a "Playfair Display" para encabezados y "Inter" para cuerpo.
    - Componentes personalizados: `glass-panel`, `form-input`, `btn-elegant`, `glass-table` aplicados consistentemente.
    - **Plantillas Actualizadas:**
        - Admin Dashboard (`menu-admin.html`)
        - Inventario (`inventario_admin.html`, `agregar-producto.html`, `editar_producto.html`)
        - Proveedores (`proveedores.html`, `agregar-proveedor.html`, `editar_proveedor.html`)
        - Contabilidad (`balance.html`, `cuenta_resultados.html`, `diario.html`, `nuevo_asiento.html`)
        - Autenticación (`login.html`, `registro.html`, `base.html`)

- **Mejoras Funcionales:**
    - **Flujo de Registro:** Implementada redirección automática al login tras registro exitoso, con pre-llenado del nombre de usuario (`auth.py`).
    - **Lógica de Autenticación:** Corrección en `create_admin.py` y `auth.py` para asegurar hash correcto de contraseñas.
    - **UI/UX:** Navbar inteligente que oculta enlaces de login/registro cuando el usuario está autenticado.

### Estado
- La interfaz administrativa y de contabilidad presenta una identidad visual cohesiva y profesional.
- El flujo de alta de usuarios es más fluido y reduce la fricción en el primer login.

### Pruebas ejecutadas
- **Verificación Visual:** Confirmado el rediseño en páginas de Login y Registro.
- **Verificación Lógica:** Código de redirección de registro y modelos de usuario verificado mediante revisión estática.
- **Limitaciones de Test:** La verificación automatizada de rutas protegidas (admin) fue bloqueada por problemas de persistencia de sesión en el entorno de pruebas local, aunque el código subyacente está implementado correctamente.

### Pendiente / próximos pasos
1. **Solucionar Entorno Local:** Resolver problemas de autenticación en el entorno de pruebas para permitir validación e2e completa.
3. **Refactorización Admin Gráficas:** Actualizar `graficas.html` para usar colores semánticos dinámicos en los gráficos (Chart.js), similar a la implementación en cliente.
4. **Limpieza Final:** Eliminar archivos CSS obsoletos y unificar estilos.

---
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