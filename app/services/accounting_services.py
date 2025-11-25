from decimal import Decimal
from datetime import datetime
from flask import current_app
from app.db import db
from app.models import Cuenta, Asiento, Apunte
from sqlalchemy import func

def inicializar_plan_cuentas():
    """Crea las cuentas contables básicas si no existen."""
    cuentas_basicas = [
        # Activos
        {"codigo": "570", "nombre": "Caja", "tipo": "ACTIVO"},
        {"codigo": "572", "nombre": "Bancos", "tipo": "ACTIVO"},
        {"codigo": "300", "nombre": "Inventario de Mercaderías", "tipo": "ACTIVO"},
        {"codigo": "430", "nombre": "Clientes", "tipo": "ACTIVO"},
        
        # Pasivos
        {"codigo": "400", "nombre": "Proveedores", "tipo": "PASIVO"},
        {"codigo": "475", "nombre": "Hacienda Pública Acreedora", "tipo": "PASIVO"},
        
        # Patrimonio
        {"codigo": "100", "nombre": "Capital Social", "tipo": "PATRIMONIO"},
        
        # Ingresos
        {"codigo": "700", "nombre": "Ventas de Mercaderías", "tipo": "INGRESO"},
        
        # Gastos
        {"codigo": "600", "nombre": "Compras de Mercaderías", "tipo": "GASTO"},
        {"codigo": "628", "nombre": "Suministros (Luz, Agua)", "tipo": "GASTO"},
        {"codigo": "693", "nombre": "Pérdidas por Deterioro", "tipo": "GASTO"}, # Costo de ventas
    ]

    for data in cuentas_basicas:
        cuenta = Cuenta.query.filter_by(codigo=data["codigo"]).first()
        if not cuenta:
            nueva_cuenta = Cuenta(codigo=data["codigo"], nombre=data["nombre"], tipo=data["tipo"])
            db.session.add(nueva_cuenta)
    
    try:
        db.session.commit()
        current_app.logger.info("Plan de cuentas inicializado.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al inicializar plan de cuentas: {e}")

def obtener_cuenta_por_codigo(codigo):
    return Cuenta.query.filter_by(codigo=codigo).first()

def crear_asiento(descripcion, usuario_id, fecha=None, referencia_id=None, apuntes_data=[]):
    """
    Crea un asiento contable con sus apuntes.
    apuntes_data: lista de dicts {'cuenta_codigo': str, 'debe': Decimal, 'haber': Decimal}
    """
    # Validar que debe == haber
    total_debe = sum(Decimal(a['debe']) for a in apuntes_data)
    total_haber = sum(Decimal(a['haber']) for a in apuntes_data)
    
    if total_debe != total_haber:
        raise ValueError(f"El asiento está descuadrado: Debe={total_debe}, Haber={total_haber}")

    asiento = Asiento(descripcion=descripcion, usuario_id=usuario_id, referencia_id=referencia_id, fecha=fecha)
    db.session.add(asiento)
    db.session.flush() # Para obtener el ID del asiento

    for apunte_dict in apuntes_data:
        cuenta = obtener_cuenta_por_codigo(apunte_dict['cuenta_codigo'])
        if not cuenta:
            inicializar_plan_cuentas()
            cuenta = obtener_cuenta_por_codigo(apunte_dict['cuenta_codigo'])
        if not cuenta:
            raise ValueError(f"Cuenta no encontrada: {apunte_dict['cuenta_codigo']}")
        
        apunte = Apunte(
            cuenta_id=cuenta.id,
            debe=Decimal(apunte_dict['debe']),
            haber=Decimal(apunte_dict['haber'])
        )
        apunte.asiento = asiento
        db.session.add(apunte)
    
    return asiento

def obtener_saldo_cuenta(cuenta_id):
    """Calcula el saldo de una cuenta (Debe - Haber para Activos/Gastos, Haber - Debe para Pasivos/Ingresos)."""
    cuenta = db.session.get(Cuenta, cuenta_id)
    if not cuenta:
        return Decimal(0)
    
    apuntes = Apunte.query.filter_by(cuenta_id=cuenta_id).all()
    total_debe = sum(a.debe for a in apuntes)
    total_haber = sum(a.haber for a in apuntes)
    
    if cuenta.tipo in ['ACTIVO', 'GASTO']:
        return total_debe - total_haber
    else:
        return total_haber - total_debe

def calcular_pmp(producto_id, cantidad_nueva, costo_nuevo):
    """
    Calcula el Precio Medio Ponderado (PMP) tras una nueva entrada de stock.
    Formula: ((Stock_Actual * Costo_Actual) + (Cantidad_Nueva * Costo_Nuevo)) / (Stock_Actual + Cantidad_Nueva)
    """
    from app.models import Producto
    producto = db.session.get(Producto, producto_id)
    if not producto:
        raise ValueError("Producto no encontrado")
    
    cantidad_actual = Decimal(producto.cantidad)
    costo_actual = Decimal(producto.costo)
    cantidad_nueva = Decimal(cantidad_nueva)
    costo_nuevo = Decimal(costo_nuevo)
    
    # Si no hay stock actual, el costo es el nuevo
    if cantidad_actual <= 0:
        return costo_nuevo
        
    valor_total = (cantidad_actual * costo_actual) + (cantidad_nueva * costo_nuevo)
    cantidad_total = cantidad_actual + cantidad_nueva
    
    if cantidad_total == 0:
        return Decimal(0)
        
    pmp = valor_total / cantidad_total
    return pmp.quantize(Decimal("0.01"))

def obtener_cuenta_resultados(fecha_inicio=None, fecha_fin=None):
    """
    Calcula la Cuenta de Resultados (Ingresos - Gastos).
    Retorna un diccionario con el desglose por cuenta y los totales.
    """
    query = db.session.query(Cuenta, func.sum(Apunte.haber - Apunte.debe).label('saldo'))\
        .join(Apunte)\
        .join(Asiento)\
        .filter(Cuenta.tipo.in_(['INGRESO', 'GASTO']))\
        .group_by(Cuenta.id)

    if fecha_inicio:
        query = query.filter(Asiento.fecha >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Asiento.fecha <= fecha_fin)
        
    resultados = query.all()
    
    ingresos = []
    gastos = []
    total_ingresos = Decimal(0)
    total_gastos = Decimal(0)
    
    for cuenta, saldo in resultados:
        # Para Ingresos, saldo positivo es Haber > Debe (Correcto)
        # Para Gastos, saldo positivo es Haber > Debe (Incorrecto, deberia ser negativo)
        # Ajustamos el signo para visualización
        
        if cuenta.tipo == 'INGRESO':
            ingresos.append({'cuenta': cuenta, 'saldo': saldo})
            total_ingresos += saldo
        elif cuenta.tipo == 'GASTO':
            # Gastos suelen tener saldo Deudor (Debe > Haber), por lo que 'saldo' (Haber-Debe) será negativo.
            # Lo convertimos a positivo para mostrar "Gasto de X: 100"
            saldo_gasto = -saldo
            gastos.append({'cuenta': cuenta, 'saldo': saldo_gasto})
            total_gastos += saldo_gasto
            
    resultado_neto = total_ingresos - total_gastos
    
    return {
        'ingresos': ingresos,
        'gastos': gastos,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'resultado_neto': resultado_neto
    }
