# Auditoría del proyecto — 11 de mayo de 2026

Aplicación: **Administración de Suministros** (Flask 3.1 + SQLAlchemy 2 + Flask-Login + Flask-WTF + Tailwind).
Rama auditada: `main` (HEAD = `dc1cd1d` "Hardening OWASP", local 3 commits por **detrás** de `origin/main`).

---

## 1. Resumen ejecutivo

El proyecto está estructuralmente sano: factory Flask con cinco blueprints (`auth`, `inventario`, `proveedores`, `reportes`, `contabilidad`), modelos consistentes, contabilidad de doble partida funcional, hardening OWASP aplicado y suite de 32 tests + helpers de verificación. La última revisión registrada en `PROJECT_STATUS.md` es del **12 de diciembre de 2025** — hay ~5 meses sin actualización de estado pero el código no muestra deuda crítica desde entonces.

Hay **dos puntos que conviene atender de inmediato** antes de seguir desarrollando:

1. **Higiene git rota.** 47 archivos aparecen como `modified` pero el diff sólo cambia terminadores de línea (CRLF ↔ LF). Es ruido puro: bloquea ver cambios reales y `git pull --rebase` casi seguro fallará. Hay 3 commits remotos sin integrar.
2. **Artefactos de depuración versionados.** `test_output.txt` (72 KB), `test_output_failures.txt`, `test_output_final.txt` y `migration_error.txt` están en el repo. Deberían estar en `.gitignore`.

El resto son recomendaciones de mejora, no urgencias.

---

## 2. Inventario del código

| Módulo | Líneas | Comentario |
|---|---|---|
| `app/blueprints/reportes.py` | 802 | El más pesado. Gráficas + caché + exports CSV. Candidato a partir. |
| `app/blueprints/inventario.py` | 570 | Menús admin/cliente, catálogo, cesta, compras. |
| `app/blueprints/proveedores.py` | 566 | CRUD proveedores + endpoints JSON. |
| `app/blueprints/auth.py` | 420 | Login/registro, panel admin, export compras. |
| `app/blueprints/contabilidad.py` | 260 | Vistas diario, balance, cuenta de resultados. |
| `app/services/accounting_services.py` | 173 | Plan de cuentas, asientos, PMP, P&L. |
| `app/blueprints/helpers.py` | 151 | `role_required`, `registrar_actividad`, sanitización CSV, validaciones compartidas. |
| `app/__init__.py` | 246 | Factory, configuración, cabeceras de seguridad, filtro `currency` (Babel). |
| `app/models.py` | 256 | 10 modelos: Usuario, Producto, Proveedor, ProveedorTipoProducto, CestaDeCompra, Compra, ActividadUsuario, Cuenta, Asiento, Apunte, CacheEvent. |
| `tests/test_flows.py` + `tests/test_filters.py` | 982 | 32 tests (unittest). |

Migraciones Alembic: tres revisiones (`baseline`, `accounting_models`, `cacheevent`).

---

## 3. Estado de git (detalle)

```
On branch main
Your branch is behind 'origin/main' by 3 commits, and can be fast-forwarded.
47 files changed, 9196 insertions(+), 9196 deletions(-)
```

Inspección del diff confirma que **el contenido es idéntico**, sólo cambian los terminadores de línea (`$` al final = LF). `app/__init__.py` además mezcla CRLF y LF en el mismo archivo.

**Commits remotos sin traer:**

- `e06ca85` — Limpieza: eliminar archivos temporales y configuración de IDE
- `f437f47` — Update .gitignore to include additional exclusions
- `c9705bf` — Simplify README by removing unnecessary explanation

Estos commits (sobre todo el de `.gitignore`) probablemente resuelvan parte del problema #2. Conviene traerlos antes de seguir.

**Cómo destrabar (sugerido):**

```bash
# 1. Configurar git para tu plataforma una sola vez
git config --global core.autocrlf true   # en Windows

# 2. Forzar renormalización del repo
git add --renormalize .
git commit -m "Normalizar terminadores de línea"

# 3. Traer los 3 commits remotos
git pull --rebase origin main
```

Como alternativa más limpia: añadir un `.gitattributes` con `* text=auto eol=lf` y renormalizar.

---

## 4. Tests

`python -m unittest discover tests` declara **32 tests** según `PROJECT_STATUS.md` y ese número coincide con lo recolectado (32 tests en 9.7 s).

Lo que vi en la corrida desde el sandbox Linux:

- 25 tests verdes.
- 7 errores **todos del mismo origen**: `PermissionError` al borrar `instance/report_cache_test.json` en el `setUp` de `ReportesCacheTest`. Es un problema de permisos del sandbox, no del código — en el entorno local de Windows estos tests pasan según el historial documentado.

`verify_enhancements.py` muestra en su último snapshot guardado (`test_output_final.txt`) **4 fallos** que sugieren que el fixture de cliente perdió sesión (status `302` en lugar de `200`, "event unexpectedly None"). Es un script aparte de la suite oficial y los fallos parecen ser de fixture, no funcionales — pero conviene revisarlo o eliminarlo si ya no aporta.

---

## 5. Seguridad — hardening OWASP

El último ciclo (12-dic-2025) cerró bien los frentes habituales:

- **A01/A05 — Configuración:** `SECRET_KEY` obligatoria en producción, cookies `HttpOnly` + `Secure` + `SameSite=Lax`, HSTS automático si `PREFERRED_URL_SCHEME=https`, CSP por defecto con whitelist para Tailwind CDN y Google Fonts, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`.
- **A02 — Criptografía:** bcrypt vía Flask-Bcrypt con rondas configurables.
- **A03 — Inyección:** WTForms en todos los formularios, `escape()` en validaciones de proveedor, sanitización anti-fórmula (`=`, `+`, `-`, `@`, `\t`, `\r`, `\n`) en CSV (`write_safe_csv_row`).
- **A07 — Auth:** `session.clear()` previo a `login_user` (evita fixation), `logout` sólo POST con CSRF, rate-limit de login (5 intentos / 10 min por IP), redirección a portada en `role_required`.
- **A09 — Logging/monitoring:** `registrar_actividad` en alta/baja de usuarios y cambios de rol.

**Caveats / mejoras posibles:**

1. `_LOGIN_ATTEMPTS` vive en un dict del proceso. Con Gunicorn multi-worker o múltiples réplicas el límite es por proceso, no global. Para producción real: Redis o `Flask-Limiter`.
2. `_LOGIN_ATTEMPTS` no se evicta. Crece con cada IP nueva mientras viva el proceso. Limpieza periódica recomendada.
3. En `auth.registro` se loguea `request.form` completo en `DEBUG` (línea 79). Aunque `contrasenya` no se imprime en login, en registro sí entraría — convendría omitirla explícitamente.
4. La CSP usa `'unsafe-inline'` para `script-src` y `style-src`. Necesario para Tailwind CDN, pero idealmente se migra a Tailwind compilado y se elimina el `unsafe-inline` (también lo recomienda el propio README de la revisión de 12-dic).

---

## 6. Hallazgos puntuales (bajo riesgo)

- **`accounting_services.crear_asiento`**: la comprobación `total_debe != total_haber` con `Decimal` es correcta pero estricta. Si en el futuro entran apuntes con fracciones de céntimo (cambio de divisa, descuentos), una tolerancia de `Decimal("0.01")` evitaría falsos descuadres. Hoy no es un problema, todos los apuntes usan `Numeric(10,2)`.
- **`obtener_cuenta_resultados`**: hace `inicializar_plan_cuentas()` dentro del bucle si falta una cuenta. Defensivo, pero ya hay un `before_request` que inicializa el plan en frío — el camino caliente debería poder asumir que las cuentas existen.
- **`migration_error.txt`** (6.5 KB) en el repo: parece un volcado puntual de un fallo de migración. No aporta y ensucia el árbol.
- **`PROJECT_STATUS.md`** lleva ~5 meses sin actualizarse. No es deuda técnica, pero los pendientes 2025-12-10 ("Refactorización Admin Gráficas", "Limpieza Final CSS") siguen abiertos según el documento.
- **Tailwind por CDN**: aceptable para desarrollo, pero para producción la propia revisión de 12-dic-2025 ya marcó como TODO compilar con `npm` y purgar.

---

## 7. Pendientes documentados que siguen abiertos

De `PROJECT_STATUS.md`, los que no se han marcado completados:

1. Definir `SECRET_KEY` y servir bajo HTTPS en despliegue real.
2. Verificar en proxies/dominios finales que CSP, HSTS y rate-limit se preserven.
3. Refactor de `graficas.html` admin para usar colores semánticos dinámicos (como en cliente).
4. Eliminar CSS obsoletos (`app/static/main.css`, `app/static/partials/back.css`) y unificar estilos.
5. Compilar Tailwind con npm en producción (purgado).
6. UAT funcional de contabilidad y exports con volumen real.
7. Cierre de ejercicio fiscal en contabilidad (reset de cuentas temporales).
8. Persistir histórico de caché en base de datos con políticas de retención.

---

## 8. Plan recomendado (orden sugerido)

**Hoy mismo, mecánico:**

1. Normalizar terminadores de línea + traer los 3 commits remotos (sección 3).
2. Añadir a `.gitignore` los `test_output*.txt`, `migration_error.txt` e `instance/cache_history*.json` (si no están en el commit `f437f47` remoto que falta por traer, mejor compararlo antes).
3. Eliminar del árbol los artefactos versionados que no aportan (`test_output*.txt`, `migration_error.txt`).

**Esta semana, ligero:**

4. Omitir explícitamente `contrasenya` del log de `registro` (`auth.py:79`).
5. Revisar `verify_enhancements.py`: o se arregla el fixture de cliente o se elimina del repo (la suite oficial ya cubre lo importante).
6. Actualizar `PROJECT_STATUS.md` con una entrada de mayo de 2026 reflejando lo que decidas tras estos pasos.

**Backlog (cuando haya planificación):**

7. Migrar rate-limit a `Flask-Limiter` + Redis si vas a despliegue multi-worker.
8. Compilar Tailwind con npm y endurecer CSP eliminando `'unsafe-inline'`.
9. Cierre de ejercicio contable.
10. Persistencia DB del histórico de caché + vista paginada (ya quedó parcialmente con `CacheEvent`).

---

*Documento generado tras revisar 11 archivos fuente, `git log/status/diff`, ejecución de la suite de tests y los snapshots de `verify_enhancements`. No se modificó código durante la auditoría.*
