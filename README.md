# Suministros CNCV — Administración de Suministros Informáticos

Aplicación web Flask para la gestión integral de un negocio de suministros informáticos: inventario, proveedores, ventas, contabilidad de doble entrada y panel de analítica. Soporta dos roles (administrador y cliente) con flujos separados.

> **Estado**: en producción local. 34 tests OK. CSP estricta. Design system documentado. 4 temas visuales (`elegant`, `cyberpunk`, `corporate`, `emerald`).

---

## Stack

| Capa | Tecnología |
|---|---|
| **Backend** | Flask 3.1, SQLAlchemy 2, Flask-Login, Flask-WTF, Flask-Bcrypt, Flask-Migrate |
| **Base de datos** | SQLite por defecto (`instance/administracion.db`); cualquier dialecto compatible con SQLAlchemy |
| **Frontend** | Jinja2 + Tailwind CSS **compilado con npm** (no CDN runtime), Chart.js para analítica |
| **Diseño** | 4 temas con tokens CSS (`primary`, `canvas`) + 4 paletas semánticas (`success`, `danger`, `warning`, `info`) |
| **Seguridad** | CSP estricta con `nonce` per-request, CSRF global, bcrypt para contraseñas, headers HSTS/X-Frame-Options/etc. |
| **Pruebas** | `unittest` con SQLite en memoria; 34 tests cubren auth, flujos de compra, reportes y renderizado de contabilidad |

---

## Setup rápido

### Requisitos
- Python 3.11+ (probado en 3.13)
- Node.js 18+ y npm (sólo para compilar el CSS; el servidor Flask no lo necesita en runtime)

### Backend
```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate      # macOS/Linux

pip install -r requirements.txt
```

### Frontend (CSS)
```bash
npm install
npm run build:css             # one-shot, produce app/static/css/tailwind.css
# o, durante desarrollo:
npm run dev:css               # watch mode (rebuild al guardar)
```

### Variables de entorno mínimas
```bash
SECRET_KEY=cambia-esto-por-algo-aleatorio
FLASK_ENV=development         # 'production' en deploy real
DATABASE_URI=sqlite:///instance/administracion.db   # opcional, es el default
```

Variables opcionales:
- `WTF_CSRF_ENABLED`: deja CSRF activo. Sólo `false` para tests automatizados.
- `SQLALCHEMY_ECHO`: `true` imprime el SQL ejecutado — útil en desarrollo, **nunca en producción**.
- `CONTENT_SECURITY_POLICY`: si quieres sobreescribir la CSP por defecto. Acepta el placeholder literal `{nonce}` que se sustituye per-request.
- `PREFERRED_URL_SCHEME=https`: activa HSTS automáticamente.

---

## Ejecutar

| Comando | Qué hace |
|---|---|
| `python run.py` | Arranca el dev server en `http://127.0.0.1:5000` |
| `npm run dev:css` | Watch mode de Tailwind (recomendado correr en paralelo al server) |
| `python -m unittest discover tests` | Corre toda la suite (34 tests, ~10s) |
| `npm run build:css` | Build CSS para producción (minified) |

---

## Estructura del proyecto

```
.
├── app/
│   ├── __init__.py             # create_app(), CSP, security headers
│   ├── blueprints/             # rutas por área temática
│   │   ├── auth.py             # login, registro, gestión de usuarios
│   │   ├── inventario.py       # menú admin/cliente, catálogo, cesta, pedidos
│   │   ├── proveedores.py      # CRUD proveedores y productos
│   │   ├── reportes.py         # gráficas y endpoints de datos
│   │   └── contabilidad.py     # diario, balance, cuenta de resultados
│   ├── services/               # lógica de negocio (contabilidad, etc.)
│   ├── models.py               # modelos SQLAlchemy
│   ├── forms.py                # formularios WTForms
│   ├── extensions.py           # csrf, login_manager, bcrypt
│   ├── static/
│   │   ├── css/
│   │   │   ├── input.css       # fuente (tokens + componentes + Tailwind layers)
│   │   │   └── tailwind.css    # COMPILADO (commiteado para deploys sin npm)
│   │   └── js/
│   │       ├── theme.js        # pre-paint theme switcher (anti-flash)
│   │       └── ui.js           # modal, toast, mobile nav, delegated handlers
│   └── templates/              # Jinja2 (extienden todos de base.html)
├── tests/
│   ├── test_flows.py           # flujos end-to-end (auth, compras, reportes…)
│   └── test_filters.py         # filtros Jinja custom
├── migrations/                 # Flask-Migrate (Alembic)
├── instance/                   # SQLite DB local (gitignored)
├── DESIGN_SYSTEM.md            # ← guía visual completa (tokens, componentes, do's/don'ts)
├── PROJECT_STATUS.md           # bitácora de cambios por sesión
├── package.json                # tailwindcss dev dependency
├── tailwind.config.js          # extensión de colores + safelist
└── run.py                      # entry point del dev server
```

---

## Frontend & Design System

El frontend está documentado por completo en **[`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md)**: tokens de color y tipografía, componentes (`glass-panel`, `glass-table`, `form-input`, `btn-primary`, etc.), patrones de página, modal/toast APIs, y guía de cómo añadir una pantalla o un tema nuevo.

**Reglas clave para mantener consistencia**:
- Nunca uses colores Tailwind hardcoded (`text-red-400`, `bg-emerald-500/10`). Usa tokens semánticos (`text-danger-400`, `bg-success-500/10`).
- Para confirmaciones destructivas, usa el modal del design system (`data-confirm="…"` o `await window.confirmDialog(...)`). Nunca `confirm()` nativo.
- Para feedback de éxito/error en JS, usa `window.showToast(message, variant)`. Nunca `alert()` nativo.
- Si añades un `<script>` inline en un template, ponle `nonce="{{ csp_nonce() }}"` o la CSP lo bloqueará.

---

## Seguridad

- **CSP estricta** sin `script-src 'unsafe-inline'`. Cada `<script>` inline lleva `nonce="{{ csp_nonce() }}"` generado por request en `app/__init__.py::_generate_csp_nonce`.
- **CSRF global** vía Flask-WTF. Activo por defecto; sólo `false` en `tests/`.
- **Contraseñas** hasheadas con bcrypt (Flask-Bcrypt). Nunca se almacenan ni se logan en claro (los logs del formulario de registro filtran campos sensibles).
- **Headers de seguridad** automáticos: `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, y HSTS cuando `PREFERRED_URL_SCHEME=https`.
- **Rate limiting** básico en el endpoint de login (in-process; para multi-worker conviene Flask-Limiter + Redis).

---

## Migraciones con Flask-Migrate

```bash
export FLASK_APP=run.py          # o set FLASK_APP=run.py en Windows

# Sólo la primera vez:
flask db init

# Tras cambiar modelos:
flask db migrate -m "descripcion del cambio"
flask db upgrade
```

> El plan de cuentas contables se inicializa automáticamente en el primer arranque (`_ensure_plan_cuentas` en `app/__init__.py`).

---

## Roles y flujos

### Cliente
`/login` → `/menu-cliente` → catálogo, cesta, confirmación de compra, pedidos, perfil, gráficas personales.

### Admin
`/login` → `/menu_principal` → inventario (CRUD productos + reponer stock), proveedores (CRUD), contabilidad (diario, balance, cuenta de resultados, nuevo asiento), reportes y gráficas, actividades (auditoría + gestión de roles).

---

## Tests

```bash
python -m unittest discover tests
```

Cubre:
- Registro, login, redirección por rol, rate-limit
- Compra completa (añadir a cesta → confirmar → pedido → cancelar)
- Endpoints de datos (`/data/*`) con permisos por rol
- Gráficas cliente (cache, agregaciones, exportación)
- Renderizado de `/contabilidad/balance` y `/contabilidad/diario` (regresión contra `BuildError` por endpoints renombrados)

---

## Despliegue

El proyecto está pensado para auto-host local. Para despliegue público:

1. Variables obligatorias: `SECRET_KEY` aleatorio, `DATABASE_URI` apuntando a un Postgres/MySQL (no SQLite), `FLASK_ENV=production`, `PREFERRED_URL_SCHEME=https`.
2. Servir tras un WSGI (gunicorn, waitress) y un reverse proxy (nginx, Caddy).
3. Compilar el CSS antes de desplegar: `npm run build:css`. El archivo `app/static/css/tailwind.css` está commiteado, así que el servidor de runtime no necesita npm.
4. Considerar Flask-Limiter + Redis para rate-limiting consistente entre workers.

---

## Documentación adicional

- **[`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md)** — sistema de diseño completo
- **[`PROJECT_STATUS.md`](PROJECT_STATUS.md)** — historial de cambios y decisiones por sesión
- **[`AUDITORIA_VISUAL_2026-05-11.md`](AUDITORIA_VISUAL_2026-05-11.md)** — auditoría visual previa al sprint de refactor

---

## Licencia

Proyecto académico / personal. Uso libre.
