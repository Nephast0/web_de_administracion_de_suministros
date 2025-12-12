from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from app.db import db
from app.models import Asiento, Cuenta, Apunte
from app.forms import AsientoManualForm
from app.services.accounting_services import crear_asiento, inicializar_plan_cuentas, obtener_saldo_cuenta
from app.blueprints.helpers import write_safe_csv_row
import csv
import io
from datetime import datetime, timedelta

contabilidad_bp = Blueprint('contabilidad', __name__, template_folder='templates')

@contabilidad_bp.route('/contabilidad/setup')
@login_required
def setup():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('menu.menu_principal'))
    
    inicializar_plan_cuentas()
    flash('Plan de cuentas inicializado correctamente.', 'success')
    return redirect(url_for('contabilidad.balance'))

@contabilidad_bp.route('/contabilidad/diario')
@login_required
def diario():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('menu.menu_principal'))
    
    def _parse_date(raw):
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d')
        except ValueError:
            return None

    fecha_inicio = _parse_date(request.args.get('fecha_inicio'))
    fecha_fin = _parse_date(request.args.get('fecha_fin'))
    if fecha_fin:
        fecha_fin = fecha_fin + timedelta(days=1)

    query = Asiento.query.order_by(Asiento.fecha.desc())
    if fecha_inicio:
        query = query.filter(Asiento.fecha >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Asiento.fecha < fecha_fin)

    asientos = query.all()
    return render_template('contabilidad/diario.html', asientos=asientos, filtros={"fecha_inicio": request.args.get('fecha_inicio', ''), "fecha_fin": request.args.get('fecha_fin', '')})

@contabilidad_bp.route('/contabilidad/balance')
@login_required
def balance():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('menu.menu_principal'))
    
    cuentas = Cuenta.query.order_by(Cuenta.codigo).all()
    saldos = {c.id: obtener_saldo_cuenta(c.id) for c in cuentas}
    
    # Calcular totales por tipo
    totales = {'ACTIVO': 0, 'PASIVO': 0, 'PATRIMONIO': 0, 'INGRESO': 0, 'GASTO': 0}
    for c in cuentas:
        totales[c.tipo] += saldos[c.id]
        
    return render_template('contabilidad/balance.html', cuentas=cuentas, saldos=saldos, totales=totales)

@contabilidad_bp.route('/contabilidad/nuevo-asiento', methods=['GET', 'POST'])
@login_required
def nuevo_asiento():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('menu.menu_principal'))
    
    form = AsientoManualForm()
    
    if form.validate_on_submit():
        try:
            apuntes_data = []
            for apunte_form in form.apuntes:
                # Filtrar entradas vacías si es necesario, aunque WTForms suele enviarlas
                if apunte_form.cuenta_codigo.data:
                    apuntes_data.append({
                        'cuenta_codigo': apunte_form.cuenta_codigo.data,
                        'debe': apunte_form.debe.data,
                        'haber': apunte_form.haber.data
                    })
            
            crear_asiento(
                descripcion=form.descripcion.data,
                usuario_id=current_user.id,
                fecha=form.fecha.data,
                apuntes_data=apuntes_data
            )
            db.session.commit()
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
def cuenta_resultados():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('menu.menu_principal'))
        
    from app.services.accounting_services import obtener_cuenta_resultados

    def _parse_date(raw):
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d')
        except ValueError:
            return None
    
    fecha_inicio_raw = request.args.get('fecha_inicio')
    fecha_fin_raw = request.args.get('fecha_fin')
    fecha_inicio = _parse_date(fecha_inicio_raw)
    fecha_fin = _parse_date(fecha_fin_raw)

    datos = obtener_cuenta_resultados(fecha_inicio, fecha_fin)
    
    return render_template('contabilidad/cuenta_resultados.html', filtros={"fecha_inicio": fecha_inicio_raw or "", "fecha_fin": fecha_fin_raw or ""}, **datos)

@contabilidad_bp.route('/contabilidad/diario/exportar')
@login_required
def exportar_diario():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('menu.menu_principal'))
    
    def _parse_date(raw):
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d')
        except ValueError:
            return None

    fecha_inicio = _parse_date(request.args.get('fecha_inicio'))
    fecha_fin = _parse_date(request.args.get('fecha_fin'))
    if fecha_fin:
        fecha_fin = fecha_fin + timedelta(days=1)

    query = Asiento.query.order_by(Asiento.fecha.desc())
    if fecha_inicio:
        query = query.filter(Asiento.fecha >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Asiento.fecha < fecha_fin)

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
            
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=diario.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@contabilidad_bp.route('/contabilidad/balance/exportar')
@login_required
def exportar_balance():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('menu.menu_principal'))
    
    cuentas = Cuenta.query.order_by(Cuenta.codigo).all()
    saldos = {c.id: obtener_saldo_cuenta(c.id) for c in cuentas}
    
    si = io.StringIO()
    cw = csv.writer(si)
    write_safe_csv_row(cw, ['Código', 'Cuenta', 'Tipo', 'Saldo'])
    
    for c in cuentas:
        saldo = saldos[c.id]
        if saldo != 0:
            write_safe_csv_row(cw, [c.codigo, c.nombre, c.tipo, saldo])
            
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=balance.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@contabilidad_bp.route('/contabilidad/cuenta-resultados/exportar')
@login_required
def exportar_cuenta_resultados():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('menu.menu_principal'))
        
    from app.services.accounting_services import obtener_cuenta_resultados

    def _parse_date(raw):
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d')
        except ValueError:
            return None
    
    fecha_inicio = _parse_date(request.args.get('fecha_inicio'))
    fecha_fin = _parse_date(request.args.get('fecha_fin'))
    
    datos = obtener_cuenta_resultados(fecha_inicio, fecha_fin)
    
    si = io.StringIO()
    cw = csv.writer(si)
    
    write_safe_csv_row(cw, ['Concepto', 'Importe'])
    write_safe_csv_row(cw, ['INGRESOS', ''])
    for item in datos['ingresos']:
        cuenta = item['cuenta']
        saldo = item['saldo']
        write_safe_csv_row(cw, [f"{cuenta.codigo} - {cuenta.nombre}", saldo])
    write_safe_csv_row(cw, ['Total Ingresos', datos['total_ingresos']])
    
    cw.writerow([])
    write_safe_csv_row(cw, ['GASTOS', ''])
    for item in datos['gastos']:
        cuenta = item['cuenta']
        saldo = item['saldo']
        write_safe_csv_row(cw, [f"{cuenta.codigo} - {cuenta.nombre}", saldo])
    write_safe_csv_row(cw, ['Total Gastos', datos['total_gastos']])
    
    cw.writerow([])
    write_safe_csv_row(cw, ['RESULTADO NETO', datos['resultado_neto']])
            
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=cuenta_resultados.csv"
    output.headers["Content-type"] = "text/csv"
    return output
