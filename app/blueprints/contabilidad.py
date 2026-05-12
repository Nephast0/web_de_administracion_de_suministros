"""Blueprint de contabilidad de doble partida.

Patrones aplicados (rediseño 2026-05-12 noche / arquitectura ADR-001):
- `role_required("admin")` consistente en todos los endpoints (antes inline).
- `registrar_actividad(...)` en mutaciones y exports (audit log completo).
- Helper `_parse_date` y `_build_diario_query` extraídos para DRY.
"""

import csv
import io
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user

from app.db import db
from app.models import Asiento, Cuenta, Usuario
from app.forms import AsientoManualForm
from app.services.accounting_services import crear_asiento, inicializar_plan_cuentas, obtener_saldo_cuenta
from app.blueprints.helpers import write_safe_csv_row, role_required, registrar_actividad


contabilidad_bp = Blueprint('contabilidad', __name__, template_folder='templates')


# ---------- Helpers locales (DRY: antes repetido 4 veces) ----------

def _parse_date(raw):
    """Parsea YYYY-MM-DD a datetime; devuelve None si vacío o inválido."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d')
    except ValueError:
        return None


def _build_diario_query(args):
    """Construye la query del diario con filtros avanzados.

    Filtros soportados (todos opcionales, AND-combinables):
      - fecha_inicio / fecha_fin   : rango de fechas (YYYY-MM-DD)
      - cuenta                     : código de cuenta a buscar dentro de los apuntes
      - usuario                    : substring del nombre de usuario que registró
      - descripcion                : substring de la descripción del asiento
    Retorna (query, filtros_dict) donde filtros_dict son los valores crudos
    para volver a poblar el form.
    """
    fecha_inicio_raw = args.get('fecha_inicio') or ''
    fecha_fin_raw    = args.get('fecha_fin') or ''
    cuenta_raw       = (args.get('cuenta') or '').strip()
    usuario_raw      = (args.get('usuario') or '').strip()
    descripcion_raw  = (args.get('descripcion') or '').strip()

    fecha_inicio = _parse_date(fecha_inicio_raw)
    fecha_fin    = _parse_date(fecha_fin_raw)
    if fecha_fin:
        # Inclusivo: incluir todo el día final.
        fecha_fin = fecha_fin + timedelta(days=1)

    query = Asiento.query.order_by(Asiento.fecha.desc())

    if fecha_inicio:
        query = query.filter(Asiento.fecha >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Asiento.fecha < fecha_fin)
    if descripcion_raw:
        query = query.filter(Asiento.descripcion.ilike(f'%{descripcion_raw}%'))
    if usuario_raw:
        # Join contra Usuario para filtrar por nombre de cuenta de usuario.
        query = query.join(Usuario, Asiento.usuario_id == Usuario.id) \
                     .filter(Usuario.usuario.ilike(f'%{usuario_raw}%'))
    if cuenta_raw:
        # Asientos cuyo cualquier apunte sea de la cuenta buscada (por código exacto o substring).
        from app.models import Apunte
        sub = db.session.query(Apunte.asiento_id) \
            .join(Cuenta, Apunte.cuenta_id == Cuenta.id) \
            .filter(Cuenta.codigo.ilike(f'%{cuenta_raw}%')).subquery()
        query = query.filter(Asiento.id.in_(sub))

    filtros = {
        "fecha_inicio": fecha_inicio_raw,
        "fecha_fin":    fecha_fin_raw,
        "cuenta":       cuenta_raw,
        "usuario":      usuario_raw,
        "descripcion":  descripcion_raw,
    }
    return query, filtros


# ---------- Endpoints ----------

@contabilidad_bp.route('/contabilidad/setup')
@login_required
@role_required("admin")
def setup():
    inicializar_plan_cuentas()
    registrar_actividad(current_user.id, "Inicializó el plan de cuentas", "Contabilidad")
    flash('Plan de cuentas inicializado correctamente.', 'success')
    return redirect(url_for('contabilidad.balance'))


@contabilidad_bp.route('/contabilidad/diario')
@login_required
@role_required("admin")
def diario():
    query, filtros = _build_diario_query(request.args)
    asientos = query.all()
    cuentas = Cuenta.query.order_by(Cuenta.codigo).all()
    return render_template(
        'contabilidad/diario.html',
        asientos=asientos,
        filtros=filtros,
        cuentas=cuentas,
    )


@contabilidad_bp.route('/contabilidad/balance')
@login_required
@role_required("admin")
def balance():
    tipo_filtro = (request.args.get('tipo') or '').upper().strip()

    cuentas_query = Cuenta.query.order_by(Cuenta.codigo)
    if tipo_filtro in {'ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO'}:
        cuentas_query = cuentas_query.filter(Cuenta.tipo == tipo_filtro)
    cuentas = cuentas_query.all()

    # Saldos sobre TODAS las cuentas (no filtradas) para que los totales no
    # se rompan al filtrar por tipo.
    all_cuentas = Cuenta.query.all()
    saldos = {c.id: obtener_saldo_cuenta(c.id) for c in all_cuentas}

    # Totales por tipo. setdefault es defensivo ante tipos importados con casing raro.
    totales = {'ACTIVO': 0, 'PASIVO': 0, 'PATRIMONIO': 0, 'INGRESO': 0, 'GASTO': 0}
    for c in all_cuentas:
        totales.setdefault(c.tipo, 0)
        totales[c.tipo] += saldos[c.id]

    return render_template(
        'contabilidad/balance.html',
        cuentas=cuentas,
        saldos=saldos,
        totales=totales,
        filtros={'tipo': tipo_filtro},
    )


@contabilidad_bp.route('/contabilidad/nuevo-asiento', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def nuevo_asiento():
    form = AsientoManualForm()

    if form.validate_on_submit():
        try:
            apuntes_data = []
            for apunte_form in form.apuntes:
                if apunte_form.cuenta_codigo.data:
                    apuntes_data.append({
                        'cuenta_codigo': apunte_form.cuenta_codigo.data,
                        'debe':  apunte_form.debe.data,
                        'haber': apunte_form.haber.data,
                    })

            asiento = crear_asiento(
                descripcion=form.descripcion.data,
                usuario_id=current_user.id,
                fecha=form.fecha.data,
                apuntes_data=apuntes_data,
            )
            db.session.commit()
            registrar_actividad(
                current_user.id,
                f"Creó asiento #{asiento.id}: {form.descripcion.data}",
                "Contabilidad",
            )
            flash('Asiento creado correctamente.', 'success')
            return redirect(url_for('contabilidad.diario'))
        except ValueError as e:
            db.session.rollback()
            flash(f'Error al crear asiento: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error inesperado: {str(e)}', 'danger')

    cuentas = Cuenta.query.order_by(Cuenta.codigo).all()
    return render_template('contabilidad/nuevo_asiento.html', form=form, cuentas=cuentas)


@contabilidad_bp.route('/contabilidad/cuenta-resultados')
@login_required
@role_required("admin")
def cuenta_resultados():
    from app.services.accounting_services import obtener_cuenta_resultados

    fecha_inicio_raw = request.args.get('fecha_inicio')
    fecha_fin_raw    = request.args.get('fecha_fin')
    fecha_inicio = _parse_date(fecha_inicio_raw)
    fecha_fin    = _parse_date(fecha_fin_raw)

    datos = obtener_cuenta_resultados(fecha_inicio, fecha_fin)

    return render_template(
        'contabilidad/cuenta_resultados.html',
        filtros={"fecha_inicio": fecha_inicio_raw or "", "fecha_fin": fecha_fin_raw or ""},
        **datos,
    )


@contabilidad_bp.route('/contabilidad/diario/exportar')
@login_required
@role_required("admin")
def exportar_diario():
    query, _filtros = _build_diario_query(request.args)
    asientos = query.all()

    si = io.StringIO()
    cw = csv.writer(si)
    write_safe_csv_row(cw, ['ID', 'Fecha', 'Descripcion', 'Usuario', 'Cuenta', 'Debe', 'Haber'])

    for asiento in asientos:
        for apunte in asiento.apuntes:
            write_safe_csv_row(
                cw,
                [
                    asiento.id,
                    asiento.fecha,
                    asiento.descripcion,
                    asiento.usuario.usuario if asiento.usuario else 'N/A',
                    f"{apunte.cuenta.codigo} - {apunte.cuenta.nombre}",
                    apunte.debe,
                    apunte.haber,
                ],
            )

    registrar_actividad(
        current_user.id,
        f"Exportó diario contable ({len(asientos)} asientos)",
        "Contabilidad",
    )

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=diario.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@contabilidad_bp.route('/contabilidad/balance/exportar')
@login_required
@role_required("admin")
def exportar_balance():
    cuentas = Cuenta.query.order_by(Cuenta.codigo).all()
    saldos = {c.id: obtener_saldo_cuenta(c.id) for c in cuentas}

    si = io.StringIO()
    cw = csv.writer(si)
    write_safe_csv_row(cw, ['Código', 'Cuenta', 'Tipo', 'Saldo'])

    rows = 0
    for c in cuentas:
        saldo = saldos[c.id]
        if saldo != 0:
            write_safe_csv_row(cw, [c.codigo, c.nombre, c.tipo, saldo])
            rows += 1

    registrar_actividad(
        current_user.id,
        f"Exportó balance ({rows} cuentas con saldo)",
        "Contabilidad",
    )

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=balance.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@contabilidad_bp.route('/contabilidad/cuenta-resultados/exportar')
@login_required
@role_required("admin")
def exportar_cuenta_resultados():
    from app.services.accounting_services import obtener_cuenta_resultados

    fecha_inicio = _parse_date(request.args.get('fecha_inicio'))
    fecha_fin    = _parse_date(request.args.get('fecha_fin'))

    datos = obtener_cuenta_resultados(fecha_inicio, fecha_fin)

    si = io.StringIO()
    cw = csv.writer(si)

    write_safe_csv_row(cw, ['Concepto', 'Importe'])
    write_safe_csv_row(cw, ['INGRESOS', ''])
    for item in datos['ingresos']:
        write_safe_csv_row(cw, [f"{item['cuenta'].codigo} - {item['cuenta'].nombre}", item['saldo']])
    write_safe_csv_row(cw, ['Total Ingresos', datos['total_ingresos']])

    cw.writerow([])
    write_safe_csv_row(cw, ['GASTOS', ''])
    for item in datos['gastos']:
        write_safe_csv_row(cw, [f"{item['cuenta'].codigo} - {item['cuenta'].nombre}", item['saldo']])
    write_safe_csv_row(cw, ['Total Gastos', datos['total_gastos']])

    cw.writerow([])
    write_safe_csv_row(cw, ['RESULTADO NETO', datos['resultado_neto']])

    registrar_actividad(
        current_user.id,
        "Exportó cuenta de resultados",
        "Contabilidad",
    )

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=cuenta_resultados.csv"
    output.headers["Content-type"] = "text/csv"
    return output
