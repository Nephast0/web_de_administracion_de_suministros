# Design System — Suministros CNCV

> Última revisión: 2026-05-12 (rediseño "serio" — paletas y tipografía reescritas).
> Stack: Flask + Jinja2 + Tailwind CSS (compilado con `npm`, sin CDN runtime).

Este documento es la fuente única de verdad para decisiones visuales y de
interacción. Si una página no cumple lo que aquí está escrito, el documento
gana — corrige la página, no el documento (a menos que sea una decisión nueva
deliberada, en cuyo caso actualízalo).

---

## 1. Filosofía

**Dashboard ejecutivo, no producto de consumo.** Inspiración: Linear, Stripe Dashboard, Notion, Vercel. La aplicación gestiona inventario, contabilidad de doble partida y operaciones reales — la interfaz debe transmitir seriedad y precisión, no entretenimiento.

Reglas que se siguen de la filosofía:

- **Glassmorphism atenuado**, no agresivo. `backdrop-blur(8px)` (antes 12px), opacidades del 55-60% (antes 35-45%). El usuario debe leer el contenido, no admirar el cristal.
- **Tipografía unificada en Inter.** La jerarquía la hace el peso y el tracking, no la familia. Adiós Playfair Display italic — era expresivo, no profesional.
- **Tokens semánticos antes que tonos crudos.** Nunca `text-emerald-400`, siempre `text-success-400`. El usuario puede cambiar de tema y el componente debe seguir teniendo sentido.
- **Radius pequeño-medio** (`rounded-md`, `rounded-lg`). Reservamos `rounded-full` para badges y avatares — no para botones de acción (que ahora son `rounded-md`).
- **Sombras planas y discretas.** Sin `shadow-2xl shadow-primary-500/25` neon glow. Una sombra debe sugerir profundidad, no llamar la atención.
- **Mínima fricción animada.** Transiciones de 150-200ms. Sin `translateY` ni `scale` exagerados.

---

## 2. Tokens

### 2.1 Color

Toda la paleta vive en variables CSS y se consume desde Tailwind via `rgb(var(--color-X) / <alpha-value>)`.

#### Tokens dependientes del tema (cambian con el theme switcher)

| Token | 50 → 950 escala | Default (theme `slate`) |
|---|---|---|
| `primary-*` | 11 tonos | Azul cobalto (`rgb(59 130 246)` en 500) |
| `canvas-*` | 11 tonos | Slate (`rgb(15 23 42)` en 900, el fondo) |

#### Los 4 temas del rediseño (2026-05-12 tarde)

| Theme | Primary 500 | Canvas 900 | Identidad |
|---|---|---|---|
| **`slate`** (default) | `rgb(59 130 246)` — azul cobalto | `rgb(15 23 42)` — slate puro | Corporativo serio. Dashboard ejecutivo, neutral. |
| **`graphite`** | `rgb(212 212 216)` — gris claro / blanco | `rgb(18 18 20)` — zinc puro | Monocromático. Apple-like, severo, contraste alto sin color. |
| **`obsidian`** | `rgb(202 138 4)` — dorado champagne | `rgb(19 16 13)` — warm black | Premium ejecutivo. Lujo discreto, "private banking". |
| **`sapphire`** | `rgb(6 182 212)` — cyan tech | `rgb(8 22 38)` — navy profundo | Tech serio. Ingeniería, dashboards técnicos. |

> **Persistencia y legado**: el tema activo se guarda en `localStorage.theme` (per navegador). Los temas antiguos (`elegant`/`cyberpunk`/`corporate`/`emerald`) se remapean automáticamente en `theme.js::normalize()` para no romper a usuarios existentes (elegant→slate, cyberpunk→sapphire, corporate→slate, emerald→obsidian).

Cada tema redefine `--color-primary-*` y `--color-canvas-*` en `[data-theme="X"]` dentro de `app/static/css/input.css`.

#### Tokens semánticos (theme-independent)

| Token | Escala | Base color | Uso |
|---|---|---|---|
| `success-*` | 11 tonos | Emerald | totales positivos, compras completadas, "money positive" |
| `danger-*`  | 11 tonos | Red     | eliminar, cancelar, errores, totales negativos |
| `warning-*` | 11 tonos | Amber   | stock bajo, pedidos pendientes, advertencias |
| `info-*`    | 11 tonos | Sky     | mensajes informativos, eventos neutros del log de caché |

> Decisión: los semánticos NO cambian por tema. Un rojo de error sigue siendo rojo en obsidian porque el usuario necesita leerlo como "error", no como "estilo".

### 2.2 Tipografía

**Una sola familia: Inter.** La jerarquía es por peso y tracking, no por familia.

| Familia | Uso |
|---|---|
| `font-sans` (Inter) | Todo el body, párrafos, formularios |
| `font-heading` (Inter, alias) | Headings — el tono ejecutivo lo dan `font-light` / `font-medium` + tracking apretado en `@layer base` |
| `font-mono` (Fira Code) | Cifras monetarias, IDs, fechas, código |

Estilos de headings aplicados en `@layer base`:

```css
h1 { font-weight: 300; letter-spacing: -0.025em; line-height: 1.15; }
h2 { font-weight: 400; letter-spacing: -0.02em;  line-height: 1.2;  }
h3 { font-weight: 500; letter-spacing: -0.015em; line-height: 1.25; }
h4 { font-weight: 500; letter-spacing: -0.01em;  line-height: 1.3;  }
```

Si un template necesita escala visual mayor para un h1, usa `font-semibold` (peso 600) en el h1 — pero NUNCA `font-bold` ni `italic`.

### 2.3 Escala de iconos canónica (5 tamaños)

Todos los `<span class="material-symbols-outlined ...">` usan **exclusivamente** uno de estos tamaños:

| Clase | px | Contexto típico |
|---|---|---|
| `text-[14px]` | 14 | inline en `text-xs` (paginación, badges micro) |
| `text-base`   | 16 | inline en `text-sm` o normal (botones pequeños, search input) |
| `text-xl`     | 20 | botones estándar, navbar items |
| `text-3xl`    | 30 | títulos de panel, dashboard pills |
| `text-4xl`    | 36 | hero icons, empty states |

### 2.4 Spacing / radius

- **Radius base de paneles**: `rounded-xl` (CSS) para `glass-panel`, `rounded-lg` para `glass-table`, `rounded-md` para `glass-card`.
- **Radius de botones**: `rounded-md` (`btn-primary`/`btn-secondary`). `rounded-full` se reserva para badges, avatares y dots de estado.
- **Padding de paneles glass**: `p-6` para paneles normales, `p-8` para hero/landing.

### 2.5 Z-index reservados

| z | Uso |
|---|---|
| `z-50`  | Navbar sticky, toast container |
| `z-[100]` | Modal de confirmación (encima del navbar) |

---

## 3. Componentes

### 3.1 `.glass-panel`
Tarjeta translúcida principal. Base de casi todo lo que no es un botón ni una tabla.
```html
<div class="glass-panel p-6 animate-fade-in">…</div>
```
- Background: `rgb(canvas-900 / 0.6)` + `backdrop-blur(8px)` (refinado en el rediseño 2026-05-12: menos blur, menos opacidad que la versión anterior).
- Borde sutil (`canvas-700 / 0.5`).
- Combinable con `animate-fade-in` y `animation-delay-X` para entrada escalonada.

### 3.2 `.glass-table`
Tabla con base glass, divisores sutiles, hover por fila SIN escalado.
```html
<table class="glass-table w-full text-sm text-left">
  <thead>…</thead>
  <tbody>…</tbody>
</table>
```
- Thead: uppercase, tracking expandido, font-size 0.7rem, font-weight 500.
- Tbody con divisores `canvas-800/0.6` y hover sutil `canvas-800/0.4` (sin tinte primary).

### 3.3 `.glass-card`
Variante de panel más compacta. Para tarjetas clicables (catálogo, links de menú).
```html
<a class="glass-card p-6 border border-canvas-700/50">…</a>
```
Hover: border `canvas-600` + background más opaco. NO `hover:scale-*` (movimiento desincronizado).

### 3.4 `.form-input`
Base para todos los inputs, selects y textareas.
```html
<input class="form-input" type="text">
<select class="form-input pr-9 appearance-none">…</select>
<textarea class="form-input">…</textarea>
```
- Border `canvas-700`, hover `canvas-600`, focus `primary-500` + ring 2px (no 3px) `primary-500/0.2`.
- `:disabled` y `[readonly]` con `opacity-0.6` y cursor `not-allowed`.

### 3.5 `.btn-primary` / `.btn-secondary`
Botones de acción. Radius `md` por defecto.
```html
<button class="btn-elegant btn-primary">
  <span class="material-symbols-outlined text-base">save</span> Guardar
</button>
<button class="btn-elegant btn-secondary">Cancelar</button>
```
- `btn-primary`: `bg-primary-600`, border del mismo color, sin shadow neon.
- `btn-secondary`: `bg-canvas-800/0.6` con border `canvas-700`.
- Ambos `rounded-md` por defecto. NUNCA `rounded-full` en ellos (rule).
- `btn-elegant` añade `filter: brightness(1.08)` en hover (sin `translateY` que rompía sombras finas).

### 3.6 Toast (snackbar) — `window.showToast(message, variant)`
Mensajes flotantes auto-dismiss tras 5s. 4 variantes: `success`, `danger`, `warning`, `info`.
```javascript
window.showToast('Usuario eliminado.', 'success');
window.showToast('No se pudo guardar.', 'danger');
```

### 3.7 Modal de confirmación — `window.confirmDialog({…})`
Reemplaza `window.confirm()` nativo. Devuelve `Promise<boolean>`. 3 variantes: `danger` (default), `warning`, `primary`.

**API declarativa** (más común):
```html
<form action="/eliminar/123" method="post"
      data-confirm="¿Estás seguro de eliminar este producto?"
      data-confirm-title="Eliminar producto"
      data-confirm-text="Eliminar"
      data-confirm-variant="danger">
  <button type="submit">Eliminar</button>
</form>
```

### 3.8 Theme switcher — vive sólo en `/perfil_cliente`
**El switcher fue removido del navbar en el rediseño 2026-05-12.** Ahora vive en la sección "Apariencia" de la pantalla de perfil. Razón: es una preferencia personal, no una herramienta de navegación, y su presencia en el navbar invitaba a juguetear con ella en mitad del trabajo.

```html
<button data-set-theme="slate" class="theme-card …">
  <span class="w-10 h-10 rounded-md" style="background: linear-gradient(135deg, …);"></span>
  <div><p class="text-sm font-medium">Slate</p><p class="text-xs text-canvas-500">Corporativo · …</p></div>
</button>
```

El handler delegado vive en `ui.js`, y `theme.js` aplica el tema pre-paint para evitar flash al cargar la página. La preferencia se guarda en `localStorage.theme`.

> Nota: ambos roles (admin y cliente) acceden a `/perfil_cliente` — el endpoint conserva el sufijo `_cliente` por compatibilidad, pero ya no lo restringe `role_required`.

---

## 4. Patrones de página

### 4.1 Wrappers canónicos (3)

| Patrón | HTML | Cuándo |
|---|---|---|
| **default** | `<div class="container mx-auto my-6 px-4 pb-12">` | Mayoría de vistas con contenido tabular o de dashboard |
| **form centrado** | `<div class="container mx-auto my-6 px-4 pb-12 flex justify-center">` | Páginas de un solo formulario que no debe ocupar todo el ancho |
| **viewport centrado** | `<div class="min-h-[75vh] flex items-center justify-center">` | Auth (login/registro) |

> El `<main>` lo provee `base.html`. **Nunca** abras otro `<main>` dentro de `{% block content %}`.

### 4.2 Botón "Volver"

Pill con icono, radius `md` (no `full`):
```html
<a href="{{ url_for('inventario.menu_principal') }}"
   class="flex items-center justify-center w-9 h-9 rounded-md border border-canvas-700 text-canvas-400 hover:text-canvas-100 hover:border-canvas-500 transition-colors bg-canvas-900/50"
   aria-label="Volver">
  <span class="material-symbols-outlined text-xl">arrow_back</span>
</a>
```

Siempre con `aria-label`. Siempre con icono `arrow_back`.

### 4.3 Headings

Patrón estándar para títulos de página:
```html
<div>
  <h1 class="text-2xl text-canvas-100">Proveedores</h1>
  <p class="text-sm text-canvas-500">Gestión de la cadena de suministro</p>
</div>
```

Para títulos de sección dentro de un panel:
```html
<header class="flex items-center gap-2 pb-4 mb-5 border-b border-canvas-800">
  <span class="material-symbols-outlined text-canvas-400 text-xl">badge</span>
  <h2 class="text-base text-canvas-100">Información personal</h2>
</header>
```

**Antes (eliminado)**: `text-3xl font-bold font-heading italic text-transparent bg-clip-text bg-gradient-to-r from-primary-200 to-primary-400`.
**Ahora**: `text-2xl text-canvas-100`. El peso lo hereda de `@layer base` (`font-weight: 400` para h2).

### 4.4 Animación de entrada escalonada

```html
<div class="glass-panel animate-fade-in">…primero…</div>
<div class="glass-panel animate-fade-in animation-delay-100">…segundo…</div>
<div class="glass-panel animate-fade-in animation-delay-200">…tercero…</div>
```

---

## 5. Do's y Don'ts

| ✅ Hacer | ❌ Evitar |
|---|---|
| `text-canvas-100` para títulos | `text-transparent bg-clip-text bg-gradient-to-r from-X to-Y` |
| `h1 class="text-2xl"` (peso desde base) | `h1 class="text-4xl font-bold font-heading italic"` |
| Inter en todo | Playfair Display italic (retirado en rediseño 2026-05-12) |
| `rounded-md` en botones | `rounded-full` en botones (sólo badges/avatares) |
| Sombras de profundidad (`shadow-lg`) | `shadow-2xl shadow-primary-500/25` (neon glow) |
| `text-success-400` para verde positivo | `text-emerald-400` o `text-green-400` hardcoded |
| `text-danger-400` para errores | `text-red-400` hardcoded |
| `text-primary-400` para acentos | `text-indigo-400`, `text-purple-400`, `text-pink-400` hardcoded |
| `window.confirmDialog({…})` o `data-confirm="…"` | `confirm('…')` nativo |
| `window.showToast(…)` | `alert('…')` nativo |
| `<form data-confirm="…">` declarativo | `onsubmit="return confirm(…)"` |
| `<button data-set-theme="X">` en `/perfil_cliente` | Theme switcher en navbar/login (retirado en rediseño 2026-05-12) |
| Clase `animation-delay-100` | `style="animation-delay: 100ms"` |
| `<script nonce="{{ csp_nonce() }}">` en page_scripts | `<script>` inline sin nonce |
| `{{ url_for('blueprint.endpoint') }}` en `href`/`action` | `href="/ruta-hardcoded"` |
| `<button aria-label="Acción">` en botones icon-only | Icon-only sin texto accesible |
| `getThemeColor('--color-primary-500', '#fallback')` para Chart.js | `getComputedStyle(...).getPropertyValue(...)` crudo (devuelve `"R G B"`, inválido) |

---

## 5.1 Chart.js + tokens de tema

Los CSS vars del tema se guardan como `R G B` (sin coma, sin `rgb()`) para que Tailwind las componga con `rgb(var(--color-X) / <alpha-value>)`. Chart.js NO entiende ese formato — necesita un color válido (`rgb(...)`, `rgba(...)`, hex). Por eso `graficas.html` y `graficas-cliente.html` usan helpers:

```javascript
const rawThemeColor = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const getThemeColor      = (v, fb) => { const r = rawThemeColor(v); return r ? `rgb(${r.replace(/\s+/g, ', ')})` : fb; };
const getThemeColorAlpha = (v, a, fb) => { const r = rawThemeColor(v); return r ? `rgba(${r.replace(/\s+/g, ', ')}, ${a})` : fb; };

const themeColors = {
  primary:   getThemeColor('--color-primary-500', '#3b82f6'),
  success:   getThemeColor('--color-success-500', '#10b981'),
  successBg: getThemeColorAlpha('--color-success-500', 0.25, 'rgba(16,185,129,0.25)'),
  // …
};
```

**Reglas para gráficos**:
- Para series múltiples, usa los 5 tokens semánticos del DS (`primary`, `secondary=warning`, `danger`, `info`, `success`). Si necesitas más de 5 categorías, considera variar tonos (`primary-300`, `primary-700`) en vez de meter acentos nuevos hardcoded.
- Para fills con alpha, usa `getThemeColorAlpha(var, 0.25, fallback)` — nunca concatenes `+ '40'` al `rgb(...)` (no es válido).

---

## 6. Infraestructura

### 6.1 Build CSS

```bash
# One-shot (producción)
npm run build:css          # -> app/static/css/tailwind.css (minified)

# Watch (desarrollo, junto al server Flask)
npm run dev:css            # rebuild on save
```

### 6.2 Content Security Policy

Producción usa **CSP estricta sin `script-src 'unsafe-inline'`**. Los scripts inline (en `page_scripts` por página) deben llevar `nonce="{{ csp_nonce() }}"`. El nonce se genera por request en `app/__init__.py::_generate_csp_nonce`.

CSP actual:
```
default-src 'self';
script-src 'self' https://cdn.jsdelivr.net 'nonce-XXX';
style-src 'self' https://fonts.googleapis.com 'unsafe-inline';
img-src 'self' data:;
font-src 'self' https://fonts.gstatic.com data:;
connect-src 'self';
frame-ancestors 'self';
base-uri 'self';
form-action 'self';
```

> `style-src 'unsafe-inline'` se mantiene por compatibilidad con estilos dinámicos que Chart.js inyecta. Si en el futuro se elimina esa dependencia o se proxy-wrappa, se puede endurecer también style-src.

### 6.3 Safelist Tailwind

Las clases generadas dinámicamente desde JS (variants del modal, variants del toast) están explícitas en `tailwind.config.js → safelist[]`. Si añades una variante nueva (p.ej. una variante `info` del modal), recuerda incluirla en safelist o purga la eliminará.

---

## 7. Cómo añadir una pantalla nueva

1. Crear template en `app/templates/X.html` con `{% extends "base.html" %}`.
2. Elegir wrapper canónico (§ 4.1).
3. Componer con `glass-panel` + `form-input` + `btn-elegant btn-primary`, etc.
4. Usar headings sobrios: `<h1 class="text-2xl text-canvas-100">…</h1>` (sin gradientes, sin italic).
5. Si necesita confirmación destructiva, usa `data-confirm="…" data-confirm-variant="danger"` (§ 3.7).
6. Para JS específico, usa `{% block page_scripts %}<script nonce="{{ csp_nonce() }}">…</script>{% endblock %}`.
7. Registrar el endpoint, renderizarlo desde el blueprint correspondiente.
8. Si la página linkea hacia otras, usar siempre `url_for('blueprint.endpoint')` — nunca URLs hardcoded.

---

## 8. Cómo añadir un tema nuevo

1. En `app/static/css/input.css`, añadir un selector `[data-theme="mi-tema"]` con las 22 variables `--color-primary-*` y `--color-canvas-*`.
2. En `app/static/js/theme.js`, añadir el nombre a `VALID = [...]`.
3. En `app/templates/perfil-cliente.html`, añadir un botón en la sección "Apariencia":
   ```html
   <button type="button" data-set-theme="mi-tema"
       class="theme-card group flex items-center gap-3 p-4 rounded-md border border-canvas-700 …">
     <span class="w-10 h-10 rounded-md border …"
           style="background: linear-gradient(135deg, rgb(canvas-900-rgb) 50%, rgb(primary-500-rgb) 50%);"></span>
     <div><p class="text-sm font-medium">Mi Tema</p><p class="text-xs text-canvas-500">Descripción corta</p></div>
   </button>
   ```
4. Actualizar el objeto `THEMES` del script inline al final de `perfil-cliente.html` con la etiqueta a mostrar.
5. Recompilar: `npm run build:css`.

Los tokens semánticos (`success/danger/warning/info`) NO se redefinen por tema — su semántica es global.
