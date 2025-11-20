"""Blueprint de gestión de proveedores y productos.

Se separa del resto para aislar validaciones y altas/ediciones de
inventario respecto a otras áreas de la app.
"""

from flask import abort, Blueprint, current_app as app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..db import db
from ..forms import AgregarProductoForm, ProveedorForm
from ..models import Producto, Proveedor
from .helpers import registrar_actividad, validar_datos_proveedor, role_required


proveedores_bp = Blueprint("proveedores", __name__)


@proveedores_bp.route('/tipos-producto/<proveedor_id>', methods=['GET'])
@login_required
@role_required("admin")
def obtener_tipos_producto(proveedor_id):
    try:
        proveedor = Proveedor.query.filter_by(id=proveedor_id).first()
        if not proveedor:
            return jsonify({'error': 'Proveedor no encontrado'}), 404

        tipos_producto = proveedor.tipo_producto.split(',') if proveedor.tipo_producto else []
        return jsonify({'tipos_producto': tipos_producto})
    except Exception as exc:  # pragma: no cover - feedback JSON
        return jsonify({'error': str(exc)}), 500


@proveedores_bp.route('/proveedor/<proveedor_id>', methods=['GET'])
@login_required
@role_required("admin")
def obtener_proveedor(proveedor_id):
    try:
        proveedor = Proveedor.query.filter_by(id=proveedor_id).first()
        if not proveedor:
            return jsonify({'error': 'Proveedor no encontrado'}), 404

        return jsonify({'cif': proveedor.cif})
    except Exception as exc:  # pragma: no cover - feedback JSON
        return jsonify({'error': str(exc)}), 500


MARCAS = {
    'Procesador': ['Intel', 'AMD', 'Qualcomm', 'ARM', 'Apple'],
    'Placa Base': ['Asus', 'Gigabyte', 'MSI', 'ASRock', 'Biostar'],
    'Ordenador': ['HP', 'Dell', 'Lenovo', 'Acer', 'Apple', 'Asus'],
    'Fuente': ['Corsair', 'Seasonic', 'EVGA', 'Thermaltake', 'Cooler Master'],
    'Disco Duro': ['Samsung', 'Seagate', 'Western Digital', 'Toshiba', 'Hitachi'],
    'RAM': ['Kingston', 'Corsair', 'G.Skill', 'Crucial', 'Patriot'],
    'Tarjeta Gráfica': ['NVIDIA', 'AMD', 'ASUS', 'EVGA', 'ZOTAC'],
}


@proveedores_bp.route('/get_marcas', methods=['GET'])
@login_required
@role_required("admin")
def get_marcas():
    tipo_producto = request.args.get('tipo_producto')
    app.logger.debug("Tipo de producto recibido: %s", tipo_producto)
    marcas = MARCAS.get(tipo_producto, [])
    marcas_json = [{'id': idx, 'nombre': marca} for idx, marca in enumerate(marcas)]
    return jsonify(marcas_json)


MARCAS_Y_MODELOS = {
    'Procesador': {
        'Intel': ['Core i9-13900K', 'Core i7-13700K', 'Core i5-13600K', 'Core i3-13100', 'Xeon W9-3495X'],
        'AMD': ['Ryzen 9 7950X', 'Ryzen 7 7800X3D', 'Ryzen 5 7600X', 'Ryzen 3 4100', 'Threadripper PRO 5995WX'],
        'Qualcomm': ['Snapdragon 8cx Gen 3', 'Snapdragon 8 Gen 2', 'Snapdragon 7+ Gen 2', 'Snapdragon 6 Gen 1',
                     'Snapdragon 888'],
        'ARM': ['Cortex-X4', 'Cortex-A78', 'Cortex-A55', 'Neoverse N2', 'Ethos-N78'],
        'Apple': ['M2 Ultra', 'M2 Max', 'M2 Pro', 'A17 Bionic', 'M3'],
    },
    'Placa Base': {
        'Asus': ['ROG Crosshair X670E Hero', 'TUF Gaming X570-Plus', 'PRIME Z690-P', 'ROG Strix B550-F',
                 'ProArt Z790-Creator'],
        'Gigabyte': ['Z790 AORUS Master', 'B550 AORUS Elite', 'X670 AORUS Elite AX', 'Z690 GAMING X', 'H610M H'],
        'MSI': ['MPG Z790 Carbon Wi-Fi', 'MAG B550 TOMAHAWK', 'PRO B760-P DDR4', 'MEG X670E ACE', 'H510M-A PRO'],
        'ASRock': ['X670E Taichi', 'B550M Steel Legend', 'Z690 Phantom Gaming 4', 'H570M-ITX', 'A520M-HDV'],
        'Biostar': ['RACING B550GTQ', 'Z790 VALKYRIE', 'A320MH', 'TB360-BTC PRO', 'H81MHV3'],
    },
    'Ordenador': {
        'HP': ['OMEN 45L', 'Pavilion Gaming Desktop', 'Victus 15L', 'EliteDesk 800 G9', 'Z2 G9 Tower'],
        'Dell': ['Alienware Aurora R15', 'XPS Desktop', 'OptiPlex 7000', 'Precision 3660', 'Inspiron 3910'],
        'Lenovo': ['Legion Tower 7i', 'IdeaCentre Gaming 5i', 'ThinkCentre M75q Gen 2', 'Yoga AIO 7',
                   'ThinkStation P360'],
        'Acer': ['Predator Orion 7000', 'Aspire TC-1760', 'Nitro 50', 'Veriton N', 'ConceptD 500'],
        'Apple': ['Mac Studio M2 Ultra', 'Mac Mini M2', 'iMac 24” M1', 'MacBook Pro 16” M3', 'MacBook Air 15” M2'],
        'Asus': ['ROG Strix G10', 'TUF Gaming GT301', 'ExpertCenter D5', 'ProArt Station PD5', 'Zen AiO 24'],
    },
    'Fuente': {
        'Corsair': ['RM850x (2021)', 'SF750 Platinum', 'CX750M', 'HX1200', 'TX650'],
        'Seasonic': ['FOCUS GX-850', 'PRIME TX-750', 'S12III 650W', 'X-850', 'Platinum 1000W'],
        'EVGA': ['SuperNOVA 1000 G5', '750 BQ', '600 W1', 'GQ 850', '500 BR'],
        'Thermaltake': ['Toughpower GF1 850W', 'Smart BX1 650W', 'Litepower 750W', 'TR2 S 500W', 'Grand RGB 850W'],
        'Cooler Master': ['V850 Gold', 'MWE Gold 650W', 'Elite V3 600W', 'XG Plus Platinum 750W', 'GX 550W'],
    },
    'Disco Duro': {
        'Samsung': ['970 EVO Plus 1TB', '980 PRO 1TB', '870 QVO 2TB', '990 PRO 2TB', 'T7 Shield 2TB'],
        'Seagate': ['Barracuda 2TB', 'FireCuda 520 1TB', 'IronWolf 4TB', 'SkyHawk 8TB', 'Exos X16 14TB'],
        'Western Digital': ['WD Black SN850X 1TB', 'WD Blue 2TB', 'WD Red Plus 4TB', 'WD Gold 12TB', 'WD Purple 8TB'],
        'Toshiba': ['X300 4TB', 'N300 6TB', 'Canvio Advance 2TB', 'P300 1TB', 'MG08 16TB'],
        'Hitachi': ['Ultrastar He10', 'Travelstar 7K1000', 'Deskstar NAS 4TB', 'C10K1800', '5K500 B'],
    },
    'RAM': {
        'Kingston': ['FURY Beast 16GB DDR5', 'HyperX Predator 32GB DDR4', 'ValueRAM 8GB DDR4',
                     'FURY Renegade 32GB DDR5', 'HyperX Impact 16GB DDR4'],
        'Corsair': ['Vengeance LPX 16GB DDR4', 'Dominator Platinum RGB 32GB DDR5', 'Vengeance RGB Pro 32GB DDR4',
                    'LPX 8GB DDR4', 'TWINX 16GB DDR3'],
        'G.Skill': ['Trident Z RGB 32GB DDR4', 'Ripjaws V 16GB DDR4', 'Flare X 16GB DDR5', 'Sniper X 8GB DDR4',
                    'Aegis 32GB DDR4'],
        'Crucial': ['Ballistix 16GB DDR4', 'Crucial DDR5 32GB', 'Crucial DDR4 8GB', 'Ballistix MAX 16GB DDR4',
                    'Crucial DDR3 16GB'],
        'Patriot': ['Viper Steel 32GB DDR4', 'Viper RGB 16GB DDR4', 'Signature Line 8GB DDR4',
                    'Viper Elite II 16GB DDR4', 'Viper Venom DDR5 32GB'],
    },
    'Tarjeta Gráfica': {
        'NVIDIA': ['GeForce RTX 4090', 'GeForce RTX 4080 Super', 'GeForce RTX 4070 Ti', 'GeForce RTX 4060 Ti',
                   'GeForce GTX 1650 Super'],
        'AMD': ['Radeon RX 7900 XTX', 'Radeon RX 7800 XT', 'Radeon RX 7700 XT', 'Radeon RX 7600', 'Radeon RX 6700 XT'],
        'ASUS': ['ROG Strix RTX 4090', 'TUF Gaming RTX 4080', 'Dual RTX 4060', 'ProArt RTX 4070', 'Phoenix GTX 1630'],
        'EVGA': ['EVGA FTW3 RTX 3090', 'EVGA XC3 RTX 3080', 'EVGA SC Ultra RTX 3060', 'EVGA KO RTX 2060',
                 'EVGA GT 710'],
        'ZOTAC': ['ZOTAC Gaming RTX 4090 AMP Extreme', 'ZOTAC Gaming RTX 4080 Trinity', 'ZOTAC Twin Edge RTX 3060',
                  'ZOTAC Mini RTX 3050', 'ZOTAC GT 1030'],
    },
}

PROVEEDOR_PRODUCTOS = [
    "Ordenador",
    "Tarjeta Gráfica",
    "Procesador",
    "Fuente",
    "Disco Duro",
    "RAM",
]


def _split_tipo_producto(value: str) -> list[str]:
    if not value or value.strip().lower() == "no especificado":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _render_proveedor_template(template, form, proveedor=None):
    return render_template(template, form=form, proveedor=proveedor)


def _hydrate_proveedor_form(form):
    form.productos.choices = [(opcion, opcion) for opcion in PROVEEDOR_PRODUCTOS]
    return form


def _flash_form_errors(form):
    for field_name, errors in form.errors.items():
        label = getattr(getattr(form, field_name, None), "label", None)
        friendly_name = label.text if label is not None else field_name
        for error in errors:
            flash(f"Error en {friendly_name}: {error}", "warning")


@proveedores_bp.route("/get_modelos", methods=["GET"])
@login_required
@role_required("admin")
def get_modelos():
    tipo_producto = request.args.get("tipo_producto")
    marca = request.args.get("marca")

    if tipo_producto in MARCAS_Y_MODELOS and marca in MARCAS_Y_MODELOS[tipo_producto]:
        modelos = MARCAS_Y_MODELOS[tipo_producto][marca]
        modelos_json = [{"id": idx, "modelo": modelo} for idx, modelo in enumerate(modelos)]
        return jsonify(modelos_json)

    return jsonify({"error": "No hay modelos disponibles"}), 404


@proveedores_bp.route("/agregar-producto", methods=["GET", "POST"])
@login_required
@role_required("admin")
def agregar_producto():
    proveedores = Proveedor.query.all()
    form = AgregarProductoForm()

    if form.validate_on_submit():
        try:
            proveedor = Proveedor.query.filter_by(id=form.proveedor_id.data).first()
            if not proveedor:
                flash("El proveedor seleccionado no existe", "error")
                return render_template("agregar-producto.html", proveedores=proveedores, form=form)

            nuevo_producto = Producto(
                proveedor_id=form.proveedor_id.data,
                tipo_producto=form.tipo_producto.data.strip(),
                modelo=form.modelo.data.strip(),
                descripcion=(form.descripcion.data or "").strip(),
                cantidad=form.cantidad.data,
                cantidad_minima=form.cantidad_minima.data or 0,
                precio=form.precio.data,
                marca=form.marca.data.strip(),
                num_referencia=form.num_referencia.data.strip(),
            )
            db.session.add(nuevo_producto)
            db.session.commit()

            registrar_actividad(
                usuario_id=current_user.id,
                accion=f"Se añadió producto: {nuevo_producto.modelo} con ID {nuevo_producto.id}",
                modulo="Gestión de Productos",
            )

            app.logger.info("Producto %s creado por %s", nuevo_producto.id, current_user.id)
            flash("Producto agregado con éxito", "success")
            return redirect(url_for("inventario.productos"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Error al guardar el producto")
            flash("Error al guardar el producto", "error")
            return render_template("agregar-producto.html", proveedores=proveedores, form=form)

    if request.method == "POST" and form.errors:
        # Propagamos errores de validación con CSRF activo para guiar al usuario.
        app.logger.debug("Errores de validación al agregar producto: %s", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {field}: {error}", "warning")

    return render_template("agregar-producto.html", proveedores=proveedores, form=form)


@proveedores_bp.route("/editar_producto/<string:id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def editar_producto(id):
    # db.session.get evita la API legacy y nos permite controlar el 404 manualmente.
    producto = db.session.get(Producto, id)
    if not producto:
        abort(404, description="Producto no encontrado")

    proveedor = db.session.get(Proveedor, producto.proveedor_id) if producto.proveedor_id else None

    if request.method == "POST":
        producto.descripcion = request.form["descripcion"]
        producto.cantidad = request.form["cantidad"]
        producto.cantidad_minima = request.form["cantidad_minima"]
        producto.precio = request.form["precio"]
        producto.num_referencia = request.form["num_referencia"]

        db.session.commit()

        registrar_actividad(
            usuario_id=current_user.id,
            accion=f"Editó el producto {producto.id}",
            modulo="Gestión de Productos",
        )

        flash("Producto actualizado correctamente", "success")
        return redirect(url_for("inventario.productos"))

    return render_template("editar_producto.html", producto=producto, proveedor=proveedor)


@proveedores_bp.route("/eliminar_producto/<string:id>", methods=["POST"])
@login_required
@role_required("admin")
def eliminar_producto(id):
    producto = db.session.get(Producto, id)
    if not producto:
        abort(404, description="Producto no encontrado")
    if producto:
        db.session.delete(producto)
        db.session.commit()

        registrar_actividad(
            usuario_id=current_user.id,
            accion=f"Eliminó el producto {producto.modelo} con ID {producto.id}",
            modulo="Gestión de Productos",
        )

        flash("Producto eliminado correctamente", "success")
        return redirect(url_for("inventario.productos"))
    return "Producto no encontrado", 404


@proveedores_bp.route("/proveedores", methods=["GET", "POST"])
@login_required
@role_required("admin")
def proveedores():
    app.logger.debug("Entrando en /proveedores")
    proveedores_list = Proveedor.query.all()
    app.logger.debug("Proveedores recuperados: %s", [p.id for p in proveedores_list])
    return render_template("proveedores.html", proveedores=proveedores_list)


@proveedores_bp.route('/agregar-proveedor', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def agregar_proveedor():
    app.logger.debug("Payload recibido para proveedor: %s", request.form)

    form = _hydrate_proveedor_form(ProveedorForm())

    if form.validate_on_submit():
        valido, datos_o_error = validar_datos_proveedor(form.data)

        if not valido:
            flash(datos_o_error, 'danger')
            return _render_proveedor_template('agregar-proveedor.html', form)

        try:
            nuevo_proveedor = Proveedor(**datos_o_error)
            db.session.add(nuevo_proveedor)
            db.session.commit()

            registrar_actividad(
                usuario_id=current_user.id,
                accion=f"Añadió al Proveedor {nuevo_proveedor.nombre} con ID {nuevo_proveedor.id}",
                modulo="Gestión de Proveedores",
            )

            flash('Proveedor registrado exitosamente.', 'success')
            return redirect(url_for('proveedores.proveedores'))

        except Exception as exc:  # pragma: no cover - rollback y feedback
            db.session.rollback()
            app.logger.error("Error al guardar proveedor: %s", exc)
            flash(f'Error al guardar el proveedor: {exc}', 'danger')
    elif request.method == 'POST':
        _flash_form_errors(form)

    return _render_proveedor_template('agregar-proveedor.html', form)


@proveedores_bp.route('/editar_proveedor/<string:proveedor_id>', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def editar_proveedor(proveedor_id):
    proveedor = db.session.get(Proveedor, proveedor_id)
    if not proveedor:
        abort(404, description="Proveedor no encontrado")

    form = _hydrate_proveedor_form(ProveedorForm(obj=proveedor))
    if request.method == 'GET':
        form.productos.data = _split_tipo_producto(proveedor.tipo_producto)

    if form.validate_on_submit():
        valido, datos_o_error = validar_datos_proveedor(form.data)
        if not valido:
            flash(datos_o_error, 'danger')
            return _render_proveedor_template('editar_proveedor.html', form, proveedor)

        try:
            proveedor.nombre = datos_o_error['nombre']
            proveedor.telefono = datos_o_error['telefono']
            proveedor.direccion = datos_o_error['direccion']
            proveedor.email = datos_o_error['email']
            proveedor.cif = datos_o_error['cif']
            proveedor.tasa_de_descuento = float(datos_o_error['tasa_de_descuento'])
            proveedor.iva = float(datos_o_error['iva'])
            proveedor.tipo_producto = datos_o_error['tipo_producto']

            db.session.commit()

            registrar_actividad(
                usuario_id=current_user.id,
                accion=f"Editó el producto {proveedor.nombre} con ID {proveedor.id}",
                modulo="Gestión de Productos",
            )

            flash('Proveedor actualizado exitosamente.', 'success')
            return redirect(url_for('proveedores.proveedores'))
        except Exception as exc:  # pragma: no cover - rollback y feedback
            db.session.rollback()
            app.logger.error("Error al actualizar proveedor: %s", exc)
            flash(f'Error al actualizar el proveedor: {exc}', 'error')
    elif request.method == 'POST':
        _flash_form_errors(form)

    return _render_proveedor_template('editar_proveedor.html', form, proveedor)


@proveedores_bp.route("/eliminar_proveedor/<string:id>", methods=["POST"])
@login_required
@role_required("admin")
def eliminar_proveedor(id):
    proveedor = db.session.get(Proveedor, id)
    if not proveedor:
        abort(404, description="Proveedor no encontrado")
    db.session.delete(proveedor)
    db.session.commit()

    registrar_actividad(
        usuario_id=current_user.id,
        accion=f"Eliminó el proveedor {proveedor.nombre} con ID {proveedor.id}",
        modulo="Gestión de Proveedores",
    )
    return redirect(url_for("proveedores.proveedores"))
