from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.db import db
from app.models import Asiento, Cuenta, Apunte
from app.forms import AsientoManualForm
from app.services.accounting_services import crear_asiento, inicializar_plan_cuentas, obtener_saldo_cuenta

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
    
    asientos = Asiento.query.order_by(Asiento.fecha.desc()).all()
    return render_template('contabilidad/diario.html', asientos=asientos)

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
            flash('Asiento creado correctamente.', 'success')
            return redirect(url_for('contabilidad.diario'))
        except ValueError as e:
            flash(f'Error al crear asiento: {str(e)}', 'danger')
        except Exception as e:
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
    
    # Opcional: Filtrar por fechas desde query params
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    datos = obtener_cuenta_resultados(fecha_inicio, fecha_fin)
    
    return render_template('contabilidad/cuenta_resultados.html', **datos)
