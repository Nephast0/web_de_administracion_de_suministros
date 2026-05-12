# Design System — Suministros CNCV

> Última revisión: 2026-05-12 (auditoría post-antigravity + a11y mínima).
> Stack: Flask + Jinja2 + Tailwind CSS (compilado con `npm`, sin CDN runtime).

Este documento es la fuente única de verdad para decisiones visuales y de
interacción. Si una página no cumple lo que aquí está escrito, el documento
gana — corrige la página, no el documento (a menos que sea una decisión nueva
deliberada, en cuyo caso actualízalo).

---

## 1. Filosofía

- **Glassmorphism oscuro elegante**. Paneles translúcidos con `backdrop-filter: blur(12px)` sobre un fondo con gradiente radial primario.
- **Tipografía dual**: `Inter` para body, `Playfair Display` (italic) para headings — contraste serif/sans que aporta identidad sin recargar.
- **Tokens semánticos antes que tonos crudos**. Nunca uses `text-emerald-400` directo; usa `text-success-400`. El usuario puede cambiar de tema y el componente debe seguir teniendo sentido.
- **Mínima fricción**: animaciones suaves de fade-in escalonado, transiciones de 200-300ms en hover. Si algo dura más de 500ms, probablemente está mal.

---

## 2. Tokens

### 2.1 Color

Toda la paleta vive en variables CSS y se consume desde Tailwind via `rgb(var(--color-X) / <alpha-value>)`.

#### Tokens dependientes del tema (cambian con el theme switcher)

| Token | 50 → 950 escala | Default (theme `elegant`) |
|---|---|---|
| `primary-*` | 11 tonos | Velvet Indigo (`rgb(128 90 255)` en 500) |
| `canvas-*` | 11 tonos | Dark Night (`rgb(27 32 44)` en 900, el fondo) |

4 temas registrados (revisión 2026-05-12, paletas refinadas):

| Theme | Primary 500 | Canvas 900 | Identidad |
|---|---|---|---|
| `elegant` (default) | `rgb(128 90 255)` — violet eléctrico | `rgb(27 32 44)` — azul-noche suave | Glassmorphism oscuro elegante |
| `cyberpunk` | `rgb(247 18 134)` — neon fuchsia | `rgb(14 14 14)` — carbon black | Hot pink sobre negro casi puro |
| `corporate` | `rgb(14 165 233)` — trust blue (sky) | `rgb(15 23 42)` — clean slate | Azul confianza sobre slate neutro |
| `emerald` | `rgb(16 185 129)` — fresh emerald | `rgb(22 26 23)` — forest zinc | Verde sobre zinc con tinte verde |

Cada uno redefine `--color-primary-*` y `--color-canvas-*` en `[data-theme="X"]` dentro de `app/static/css/input.css`.

#### Tokens semánticos (theme-independent)

| Token | Escala | Base color | Uso |
|---|---|---|---|
| `success-*` | 11 tonos | Emerald | totales positivos, compras completadas, "money positive" |
| `danger-*`  | 11 tonos | Red     | eliminar, cancelar, errores, totales negativos |
| `warning-*` | 11 tonos | Amber   | stock bajo, pedidos pendientes, advertencias |
| `info-*`    | 11 tonos | Sky     | mensajes informativos, eventos neutros del log de caché |

> Decisión: los semánticos NO cambian por tema. Un rojo de error sigue siendo rojo en cyberpunk porque el usuario necesita leerlo como "error", no como "estilo".

### 2.2 Tipografía

| Familia | Uso |
|---|---|
| `font-sans` (Inter) | Body, párrafos, formularios |
| `font-heading` (Playfair Display, italic) | h1, h2, h3 destacados, dashboards |
| `font-mono` (Fira Code) | Cifras monetarias, IDs, fechas, código |

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

- **Radius base de paneles**: `rounded-xl` (1rem) para `glass-panel`, `glass-card`.
- **Radius base de tablas**: `rounded-lg` (0.75rem) para `glass-table`.
- **Radius de botones**: `rounded-full` para `btn-primary`/`btn-secondary` (acción), `rounded-lg` para botones cuadrados de icono.
- **Padding de paneles glass**: `p-6` para paneles normales, `p-8` para hero/landing.

### 2.5 Z-index reservados

| z | Uso |
|---|---|
| `z-50`  | Navbar sticky |
| `z-50`  | Theme switcher dropdown |
| `z-[100]` | Modal de confirmación (encima del navbar) |
| `z-50` | Toast container |

---

## 3. Componentes

### 3.1 `.glass-panel`
Tarjeta translúcida principal. Base de casi todo lo que no es un botón ni una tabla.
```html
<div class="glass-panel p-6 animate-fade-in">…</div>
```
- Background: `rgb(canvas-800 / 0.4)` + `backdrop-blur(12px)`
- Borde sutil (`canvas-200 / 0.08`)
- Combinable con `animate-fade-in` y `animation-delay-X` para entrada escalonada.

### 3.2 `.glass-table`
Tabla con base glass, divisores suaves y hover por fila.
```html
<table class="glass-table w-full text-sm text-left">
  <thead>…</thead>
  <tbody>…</tbody>
</table>
```
- Thead con uppercase, tracking, font-size 0.75rem.
- Tbody con `divide-y` automático y hover `bg-primary-500/0.06`.

### 3.3 `.glass-card`
Variante de panel más compacta y con hover elevation.
```html
<a class="glass-card p-6 hover:scale-[1.02] border border-canvas-700/50 hover:border-primary-500/50">…</a>
```
Diseñada para tarjetas clicables (catálogo, links de menú).

### 3.4 `.form-input`
Base para todos los inputs, selects y textareas. Las utilities Tailwind que se añaden encima sobreescriben sin conflicto.
```html
<input class="form-input focus:border-primary-500 focus:ring-primary-500" type="text">
<select class="form-input">…</select>
<textarea class="form-input">…</textarea>
```
- Border `canvas-700`, hover `canvas-600`, focus `primary-500` + ring 3px.
- `:disabled` y `[readonly]` con `opacity-0.7` y cursor `not-allowed`.

### 3.5 `.btn-primary` / `.btn-secondary`
Botones de acción. Casi siempre se combinan con `.btn-elegant` para la animación de elevación al hover.
```html
<button class="btn-elegant btn-primary">
  <span class="material-symbols-outlined text-xl">save</span> Guardar
</button>
<button class="btn-elegant btn-secondary">Cancelar</button>
```
- `btn-primary` usa `bg-primary-600` con shadow de marca.
- `btn-secondary` usa `bg-canvas-800/0.7` con borde `canvas-700`.
- Ambos `rounded-full` por defecto.

### 3.6 Toast (snackbar) — `window.showToast(message, variant)`
Mensajes flotantes auto-dismiss tras 5s. 4 variantes: `success`, `danger`, `warning`, `info`.
```javascript
window.showToast('Usuario eliminado.', 'success');
window.showToast('No se pudo guardar.', 'danger');
```
Se renderiza dentro de `#toast-container` que vive en `base.html`.

### 3.7 Modal de confirmación — `window.confirmDialog({title, message, confirmText, cancelText, variant})`
Reemplaza `window.confirm()` nativo. Devuelve `Promise<boolean>`. 3 variantes: `danger` (default), `warning`, `primary`.

**API imperativa** (para flujos en JS):
```javascript
const ok = await window.confirmDialog({
  title: 'Eliminar usuario',
  message: '¿Estás seguro? Esta acción no se puede deshacer.',
  confirmText: 'Eliminar',
  variant: 'danger',
});
if (ok) { /* … */ }
```

**API declarativa** (más común — sin JS por página):
```html
<form action="/eliminar/123" method="post"
      data-confirm="¿Estás seguro de eliminar este producto?"
      data-confirm-title="Eliminar producto"
      data-confirm-text="Eliminar"
      data-confirm-variant="danger">
  <button type="submit">Eliminar</button>
</form>
```

También funciona en `<a data-confirm="…">` y `<button data-confirm="…">` (sin `type="submit"`).

### 3.8 Theme switcher — `<button data-set-theme="X">`
Cualquier elemento con `data-set-theme="..."` se conecta al theme switcher via delegated event.
```html
<button data-set-theme="cyberpunk">Cyberpunk</button>
```
Persiste el tema en `localStorage`. Aplicado pre-paint por `theme.js`.

---

## 4. Patrones de página

### 4.1 Wrappers canónicos (3)

| Patrón | HTML | Cuándo |
|---|---|---|
| **default** | `<div class="container mx-auto my-6 px-4 pb-12">` | Mayoría de vistas con contenido tabular o de dashboard |
| **form centrado** | `<div class="container mx-auto my-6 px-4 pb-12 flex justify-center">` | Páginas de un solo formulario que no debe ocupar todo el ancho |
| **viewport centrado** | `<div class="min-h-screen flex items-center justify-center p-4">` | Auth (login/registro), menú-cliente |

> El `<main>` lo provee `base.html`. **Nunca** abras otro `<main>` dentro de `{% block content %}`.

### 4.2 Botón "Volver" (2 patrones válidos según contexto)

**Pill icon-only** (la mayoría): para vistas con back-button independiente del header de página.
```html
<a href="{{ url_for('inventario.menu_principal') }}"
   class="flex items-center justify-center w-10 h-10 rounded-full border border-canvas-700 text-canvas-400 hover:text-primary-400 hover:border-primary-400 transition-all bg-canvas-900/50"
   aria-label="Volver al menú">
  <span class="material-symbols-outlined">arrow_back</span>
</a>
```

**Inline link con texto**: cuando el back-button está integrado en un `flex` con el `<h1>` (ej. `menu-admin.html`).
```html
<a href="{{ url_for('inventario.menu_principal') }}"
   class="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1 no-underline transition-colors">
  <span class="material-symbols-outlined text-base">arrow_back</span> Volver al Menú Principal
</a>
```

> Siempre con `aria-label`. Siempre con icono `arrow_back`.

### 4.3 Animación de entrada escalonada

```html
<div class="glass-panel animate-fade-in">…primero…</div>
<div class="glass-panel animate-fade-in animation-delay-100">…segundo…</div>
<div class="glass-panel animate-fade-in animation-delay-200">…tercero…</div>
```

Clases disponibles: `animation-delay-0`, `-50`, `-100`, `-150`, `-200`, `-250`, `-300`, `-400`, `-500`, `-600`.

---

## 5. Do's y Don'ts

| ✅ Hacer | ❌ Evitar |
|---|---|
| `text-success-400` para verde positivo | `text-emerald-400` o `text-green-400` hardcoded |
| `text-danger-400` para errores | `text-red-400` hardcoded |
| `text-primary-400` para acentos | `text-indigo-400` o `text-blue-400` hardcoded |
| `window.confirmDialog({…})` o `data-confirm="…"` | `confirm('…')` nativo |
| `window.showToast(…)` | `alert('…')` nativo |
| `<form data-confirm="…">` declarativo | `onsubmit="return confirm(…)"` |
| `<button data-set-theme="X">` | `onclick="setTheme('X')"` |
| `<button data-flash-close>` | `onclick="this.parentElement.style.opacity=0; …"` |
| Clase `animation-delay-100` | `style="animation-delay: 100ms"` (la CSP estricta puede romperlo) |
| `<script nonce="{{ csp_nonce() }}">` en page_scripts | `<script>` inline sin nonce |
| Un solo `<main>` (provisto por `base.html`) | Otro `<main>` dentro del bloque content |
| `{{ url_for('blueprint.endpoint') }}` en `href`/`action` | `href="/ruta-hardcoded"` (rompe si renombras endpoint) |
| `<button aria-label="Acción">` en botones icon-only | `<button>` icon-only sin texto accesible |
| `getThemeColor('--color-primary-500', '#fallback')` para Chart.js | `getComputedStyle(...).getPropertyValue(...)` crudo (devuelve `"R G B"`, inválido como color) |

---

## 5.1 Chart.js + tokens de tema

Los CSS vars del tema se guardan como `R G B` (sin coma, sin `rgb()`) para que Tailwind las componga con `rgb(var(--color-X) / <alpha-value>)`. Chart.js NO entiende ese formato — necesita un color válido (`rgb(...)`, `rgba(...)`, hex). Por eso `graficas.html` y `graficas-cliente.html` usan helpers que envuelven el valor:

```javascript
const rawThemeColor = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const getThemeColor      = (v, fb) => { const r = rawThemeColor(v); return r ? `rgb(${r.replace(/\s+/g, ', ')})` : fb; };
const getThemeColorAlpha = (v, a, fb) => { const r = rawThemeColor(v); return r ? `rgba(${r.replace(/\s+/g, ', ')}, ${a})` : fb; };

const themeColors = {
  primary:   getThemeColor('--color-primary-500', '#6366f1'),
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
npm run build:css          # -> app/static/css/tailwind.css (minified, ~45KB)

# Watch (desarrollo, junto al server Flask)
npm run dev:css            # rebuild on save
```

### 6.2 Content Security Policy

Producción usa **CSP estricta sin `script-src 'unsafe-inline'`**. Los scripts inline (en `page_scripts` por página) deben llevar `nonce="{{ csp_nonce() }}"`. El template `tailwind.config.js` lo genera por request en `app/__init__.py::_generate_csp_nonce`.

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

Las clases generadas dinámicamente desde JS (variants del modal, variants del toast) están explícitas en `tailwind.config.js` → `safelist[]`. Si añades una variante nueva (p.ej. una variante `info` del modal), recuerda incluirla en safelist o purga la eliminará.

---

## 7. Cómo añadir una pantalla nueva

1. Crear template en `app/templates/X.html` con `{% extends "base.html" %}`.
2. Elegir wrapper canónico (§ 4.1).
3. Componer con `glass-panel` + `form-input` + `btn-elegant btn-primary`, etc.
4. Si necesita confirmación destructiva, usa `data-confirm="…" data-confirm-variant="danger"` (§ 3.7).
5. Para JS específico, usa `{% block page_scripts %}<script nonce="{{ csp_nonce() }}">…</script>{% endblock %}`.
6. Registrar el endpoint, renderizarlo desde el blueprint correspondiente.
7. Si la página linkea hacia otras, usar siempre `url_for('blueprint.endpoint')` — nunca URLs hardcoded.

---

## 8. Cómo añadir un tema nuevo

1. En `app/static/css/input.css`, añadir un selector `[data-theme="mi-tema"]` con las 22 variables `--color-primary-*` y `--color-canvas-*`.
2. En `app/templates/base.html`, añadir un botón en el theme switcher dropdown:
   ```html
   <button data-set-theme="mi-tema" class="…">
     <span class="w-3 h-3 rounded-full bg-[#HEXPRIMARY]"></span> Mi Tema
   </button>
   ```
3. Recompilar: `npm run build:css`.

Los tokens semánticos (`success/danger/warning/info`) NO se redefinen por tema — su semántica es global.
