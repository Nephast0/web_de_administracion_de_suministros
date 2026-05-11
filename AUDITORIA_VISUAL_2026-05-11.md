# Auditoría visual — 2026-05-11

Aplicación: Suministros CNCV (Flask + Jinja + Tailwind CSS por CDN).
Templates auditados: **25** (todas las vistas).
Alcance: estructura HTML, sistema de tokens, componentes, consistencia cross-template, accesibilidad básica.
Modo: lectura. No se modificó nada.

---

## 1. Resumen ejecutivo

El proyecto **tiene un sistema de tokens bien diseñado** (variables CSS `--color-primary-*` y `--color-canvas-*` con 4 temas: elegant, cyberpunk, corporate, emerald) y un theme switcher funcional. Pero **la mayoría de las plantillas no usa ese sistema correctamente**, lo que provoca dos problemas serios:

1. **5 clases de componente son "fantasma" — están en uso (161 veces) pero no están definidas en ningún archivo CSS.** `form-input`, `glass-table`, `glass-card`, `btn-primary`, `btn-secondary`. Sólo `glass-panel` y `btn-elegant` están definidas en `<style>` de `base.html`. Esto significa que muchos inputs, tablas y botones se ven sólo con estilos del browser, no con el diseño "Elegant Dark" prometido.

2. **`graficas.html` admin no usa tokens** — usa `slate-*` e `indigo-*` hardcodeados. El theme switcher **no afecta esa vista**. Otros 14 templates tienen colores semánticos hardcodeados (`red-*`, `amber-*`, `emerald-*`) que tampoco cambian con el tema.

Otros 3 problemas estructurales: `<main>` anidado en 6 templates (HTML inválido), `text-decoration-none` (clase Bootstrap, no Tailwind) en 31 sitios, y duplicación de marca/logout en `menu-cliente.html`.

**Buena noticia**: la mayoría son fixes mecánicos y centralizados. Definir las 5 clases fantasma + extender la paleta semántica = ~80% del impacto.

---

## 2. Bugs visuales críticos

### 2.1 Clases fantasma (161 ocurrencias, 23 archivos)

| Clase | Apariciones | Archivos | Realmente hace |
|---|---|---|---|
| `form-input` | mayoría | casi todos los formularios | **Nada** (no definida). Inputs se ven con estilo nativo del browser. |
| `glass-table` | menu-admin, menu-cliente, varios | tablas paginadas | Nada. Las tablas se ven sin el efecto glass. |
| `glass-card` | menu-cliente | tarjetas Catálogo/Mis Métricas | Nada. La animación `hover:scale-[1.02]` sí funciona porque va aparte. |
| `btn-primary` | botones primarios | formularios, filtros | Nada. Los estilos `bg-primary-600 hover:bg-primary-500` que se ponen al lado SÍ aplican (utilities Tailwind). |
| `btn-secondary` | botones secundarios | filtros, exports, paginación | Nada. Igual que arriba. |

**Verificación rápida (lo que ve el usuario hoy):**
- Inputs sin border consistente, sin padding consistente, sin focus ring custom → aspecto "navegador 2003".
- Tablas planas sin efecto glass, divisores duros.
- Botones funcionando "de milagro" porque casi siempre llevan utilidades inline que compensan (`bg-primary-600 hover:bg-primary-500`).

**Origen**: el PROJECT_STATUS del 2025-12-10 afirmaba que estos componentes "se aplicaron consistentemente". Probablemente vivían en un `app/static/main.css` que se eliminó en la migración a Tailwind por CDN sin trasladar las definiciones.

---

### 2.2 `graficas.html` admin no responde al theme switcher

Usa `slate-*` (700, 800, 900) e `indigo-*` (200, 400, 900) hardcodeados en TODO el archivo (22 ocurrencias). El theme switcher cambia `--color-primary` y `--color-canvas`, pero `slate-*` e `indigo-*` son colores Tailwind directos.

Esto es **el pendiente de diciembre 2025 que sigue abierto** según `PROJECT_STATUS.md` ("Refactorización Admin Gráficas — colores semánticos dinámicos").

Comparativa con `graficas-cliente.html`: el cliente sí usa tokens semánticos (ver auditoría futura, pero PROJECT_STATUS lo confirma).

---

### 2.3 `<main>` anidado (6 templates → HTML inválido)

`base.html:323` ya envuelve el contenido con `<main>`. Pero 6 templates abren otro `<main>` dentro:

- `menu-admin.html:5` — `<main class="container mx-auto my-6 px-4 pb-12">`
- `menu-cliente.html:5` — `<main class="min-h-screen flex items-center justify-center p-4">`
- `registro.html:5` — `<main class="min-h-screen flex items-center justify-center p-4">`
- `inventario_admin.html:5`, `inventario.html:5`, `graficas.html:5`, etc. — patrón `<main class="container mx-auto my-6 px-4 pb-12">`

**Spec HTML**: un solo `<main>` por documento.
**Impacto a11y**: lectores de pantalla pueden saltar de forma errática entre los dos `<main>`.
**Fix**: cambiar el `<main>` interno por `<div>` con las mismas clases, o quitar el wrapper si solo aporta el container que ya viene de base.

---

### 2.4 `text-decoration-none` no hace nada (31 ocurrencias, 6 archivos)

`text-decoration-none` es clase **Bootstrap**, no Tailwind. En Tailwind el equivalente es `no-underline`. Resultado: links que se intentaba evitar que subrayaran probablemente sí están subrayados en hover (depende del browser y del estilo `link` por defecto).

**Archivos**: `inventario_admin.html`, `graficas.html`, `menu-admin.html`, `menu-cliente.html`, `productos-cliente.html`, `perfil-cliente.html`.

---

## 3. Inconsistencias sistémicas

### 3.1 Wrappers de página: 3 patrones diferentes

| Patrón | Usado en | Comentario |
|---|---|---|
| `<div class="space-y-8 animate-fade-in">` | `menu_principal.html` | Limpio. No abre `<main>`. |
| `<main class="container mx-auto my-6 px-4 pb-12">` | `inventario_admin`, `inventario`, `graficas`, `cesta`, `balance`, `pedidos`, ... | El padrón mayoritario, pero rompe a11y. |
| `<main class="min-h-screen flex items-center justify-center p-4">` | `registro`, `menu-cliente`, `index.html` (similar sin main) | Para vistas "centradas". |

**Fix**: definir 2 patrones de container (default y centered) y aplicarlos con `<div>`. El `<main>` lo provee `base.html`.

### 3.2 Colores semánticos hardcodeados (71 ocurrencias, 15 archivos)

Estados como success, danger, warning, info **no son tokens** — viven hardcoded:

- **Success**: `text-emerald-400`, `bg-emerald-500/10`, `border-emerald-500/30` (compras completadas, totales positivos)
- **Danger**: `text-red-400`, `bg-red-500/10`, `border-red-500/30` (cancelaciones, eliminar, totales negativos)
- **Warning**: `text-amber-400`, `bg-amber-500/10`, `border-amber-500/30` (stock bajo, pedidos pendientes)
- **Money positive**: `text-green-400` en `menu_principal.html`, `text-emerald-400` en `cesta.html` — **inconsistencia entre vistas** para el mismo concepto.
- **Slate legacy**: `text-slate-400`, `bg-slate-500/10` aparece como fallback en `menu-admin.html:362` y todo `graficas.html`.

**Fix**: añadir tokens semánticos a `tailwind.config` y `:root` (`--color-success`, `--color-danger`, `--color-warning`, `--color-info`). Sustituir uso a lo largo.

### 3.3 Wrappers de "Volver" duplicados

Hay dos variantes para el botón "Volver al menú":
- **Pill flotante**: `rounded-full w-10 h-10 border border-canvas-700` (cesta, balance, inventario admin, graficas, etc.)
- **Inline link**: `text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1` (menu-admin)

Ambos válidos pero conviven sin razón. Decidir uno y aplicarlo siempre.

### 3.4 Banner de marca duplicado

`base.html:190-193` ya muestra "Suministros CNCV" en el navbar. Pero:
- `index.html:8`: `<h1>Suministros CNCV</h1>`
- `menu-cliente.html:9`: `<h1>Suministros Informáticos <span>CNCV</span></h1>`
- `menu_principal.html:12`: `<h1>Suministros Informáticos CNCV</h1>`
- `registro.html:14`: gradient text "Crear Cuenta" (esta sí es título de página, OK).

En auth (`index`, `registro`) tiene sentido (no hay navbar autenticado todavía). En `menu-cliente` y `menu_principal` ya hay navbar — el banner es redundante.

### 3.5 Logout duplicado en `menu-cliente.html`

`base.html:260` ya pinta el botón "Salir" en el navbar.
`menu-cliente.html:34-41` pinta OTRO botón logout en el header de la página.

En `menu-cliente` aparecen **dos botones de cerrar sesión** simultáneamente.

### 3.6 Tamaños de icono inconsistentes

Material Symbols se dimensiona con clases Tailwind aleatorias: `text-sm`, `text-base`, `text-lg`, `text-xl`, `text-2xl`, `text-3xl`, `text-4xl`, `text-[16px]`, `text-[20px]`, `text-[10px]`. No hay escala definida.

**Fix**: 4-5 tamaños canónicos (xs/sm/md/lg/xl) y aplicarlos.

### 3.7 `confirm()` y `alert()` nativos

`menu-admin.html` y `cesta.html` (y probablemente más) usan `confirm()` y `alert()` del browser en operaciones de eliminar/cambiar rol. Choca visualmente con el resto del diseño (snackbars custom + glass panels).

**Fix**: modal de confirmación reutilizable + integrar con el sistema de flash messages existente.

---

## 4. Lo bueno (lo que sí funciona)

- **Sistema de tokens**: CSS variables + Tailwind config bien hecho. Soporta 4 temas sin tocar markup.
- **Theme switcher**: persistente vía localStorage, aplica antes de pintar (no hay flash).
- **Snackbars (`alert-dismissible`)**: bonitos, auto-hide, con iconos semánticos, accesibles con botón cerrar.
- **Animación `animate-fade-in`**: aplicada en glass-panels, da sensación de carga progresiva.
- **Tipografía**: Inter para body + Playfair Display italic para headings = identidad clara.
- **Navbar**: bien estructurado, condicional por rol/auth, dropdown del theme switcher con buen comportamiento.
- **Material Symbols Outlined**: consistente como librería de iconos en toda la app.
- **Iconografía en navbar móvil**: bien resuelto (toggle, hidden lg:flex).

---

## 5. Priorización para la fase visual

### Sprint 1 — Fixes estructurales (alta prioridad, baja-media dificultad)

1. **Definir las 5 clases fantasma** en el `<style>` de `base.html` o en un bloque separado. Estimación: 1 sesión, impacto enorme.
   - `form-input` con border/padding/focus consistentes (modo oscuro).
   - `glass-table` con backdrop-blur, divisores `canvas-700/50`, hover row.
   - `glass-card` ya casi funciona — solo añadir base.
   - `btn-primary` y `btn-secondary` con padding/radius/transition base.
2. **Resolver `<main>` anidado**: replace `<main>` interno por `<div>` en los 6 templates. 1 sesión.
3. **Reemplazar `text-decoration-none` → `no-underline`** (replace_all global). 5 minutos.
4. **Eliminar logout duplicado** en `menu-cliente.html`. 2 minutos.

### Sprint 2 — Tokens semánticos (alta prioridad, media dificultad)

5. **Añadir tokens semánticos** (`--color-success`, `--color-danger`, `--color-warning`, `--color-info`) en `:root` y cada tema, con su escala 400/500. Extender `tailwind.config.colors`. Migrar usos `emerald-400 → success-400`, etc. Estimación: 1-2 sesiones.
6. **Refactor `graficas.html` admin** para usar tokens semánticos (cierra el pendiente de dic-2025). 1 sesión.
7. **Unificar "money positive"** a un solo token (`text-success-400` o similar).

### Sprint 3 — Pulido visual (media prioridad)

8. **Wrappers consistentes**: 2 patrones de container, aplicados sistemáticamente.
9. **Escala de iconos canónica** (5 tamaños), barrido global.
10. **Modal de confirmación reutilizable** + retirar `alert/confirm` nativos.
11. **Decidir "Volver" canónico** (pill vs inline link) y aplicarlo.
12. **Decidir banner de marca** en menús internos (probablemente quitarlo).

### Sprint 4 — Infraestructura (media-baja, alta dificultad)

13. **Compilar Tailwind con npm** + purgado + eliminar `'unsafe-inline'` de CSP. Pendiente arrastrado.
14. **Formalizar mini design system** en `DESIGN_SYSTEM.md` con tokens, componentes, do's/don'ts.

---

## 6. Estimación global

- **Sprint 1 + 2** (estructural + tokens): 4-5 sesiones de trabajo focalizado.
- **Sprint 3** (pulido): 2-3 sesiones, repartibles.
- **Sprint 4** (infra): 2 sesiones, mejor cuando todo lo demás esté estable.

**Total**: 8-10 sesiones para tener todo el frente visual cerrado en un estado "design system real".

---

*Auditoría generada sin modificar código fuente. Para ejecutar cualquiera de los sprints, ver `PROJECT_STATUS.md` y elegir punto de entrada.*
