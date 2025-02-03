from functools import wraps
from glob import escape
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import forms
from forms import Formulario_de_registro, Login_form, EditarPerfilForm, ProveedorForm
from models import Usuario, Producto, db, Proveedor, ActividadUsuario, CestaDeCompra
import logging

# Configurar el logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
bcrypt = Bcrypt()
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///administracion.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
db.init_app(app)
app.config['WTF_CSRF_ENABLED'] = False
app.config["SECRET_KEY"] = "ad877c"
with app.app_context():
    db.create_all()

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def cargar_usuario(usuario_id):
    return db.session.get(Usuario, str(usuario_id))

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.rol != role:
                flash("Acceso denegado.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapped
    return decorator

def registrar_actividad(usuario_id, accion, modulo):
    """
    Registra una actividad de usuario en la base de datos.

    :param usuario_id: ID del usuario que realiza la acción
    :param accion: Descripción de la acción realizada
    :param modulo: Módulo o funcionalidad donde ocurrió la acción
    """
    try:
        nueva_actividad = ActividadUsuario(
            usuario_id=usuario_id,
            accion=accion,
            modulo=modulo
        )
        db.session.add(nueva_actividad)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al registrar la actividad: {e}")

def validar_datos_proveedor(form):
    """
    Valida y prepara los datos del formulario para guardar en la base de datos.
    Devuelve un tuple con (True, datos) si los datos son válidos, o (False, mensaje_error) si no lo son.
    """
    required_fields = ["nombre", "telefono", "direccion", "email", "cif", "tasa_de_descuento", "iva"]
    for field in required_fields:
        if not form.get(field):
            return False, f"El campo '{field}' es obligatorio."

    try:
        tasa_de_descuento = float(form.get("tasa_de_descuento"))
        iva = float(form.get("iva"))
    except ValueError:
        return False, "Los campos 'Tasa de descuento' e 'IVA' deben ser números válidos."

    # Capturar y procesar los productos seleccionados
    productos = form.getlist("productos")
    productos_str = ", ".join(productos) if productos else "No especificado"

    # Escapar y preparar los datos
    datos = {
        "nombre": escape(form.get("nombre")),
        "telefono": escape(form.get("telefono")),
        "direccion": escape(form.get("direccion")),
        "email": escape(form.get("email")),
        "cif": escape(form.get("cif")),
        "tasa_de_descuento": tasa_de_descuento,
        "iva": iva,
        "tipo_producto": productos_str,
    }
    return True, datos

@app.route("/", methods=["GET"])
def root():
    form= Login_form()
    return render_template("index.html", form= form)

@app.route("/registro", methods=["GET", "POST"])
def registro():
    form = Formulario_de_registro()

    # Verifica si el formulario se envió correctamente
    print("Método de solicitud:", request.method)
    if request.method == "POST":
        print("Datos enviados en el formulario:", request.form)

    if form.validate_on_submit():
        print("El formulario pasó las validaciones.")

        # Crea un nuevo usuario con el rol seleccionado
        try:
            nuevo_usuario = Usuario(
                nombre= form.nombre.data,
                usuario=form.usuario.data,
                direccion=form.direccion.data,
                contrasenya=form.contrasenya.data,
                rol=form.rol.data  # Guardamos el rol del usuario
            )

            print("Nuevo usuario creado:", nuevo_usuario)

            # Agrega y confirma la operación en la base de datos
            db.session.add(nuevo_usuario)
            db.session.commit()
            print("Usuario guardado en la base de datos.")

            # Registrar actividad
            registrar_actividad(
                usuario_id=nuevo_usuario.id,  # ID del usuario actual
                accion=f"Registró un nuevo usuario: {nuevo_usuario.usuario}",
                modulo="Registro de Usuario"
            )

            flash("¡Tu cuenta ha sido creada! Ahora puedes iniciar sesión.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            print("Error al intentar guardar el usuario en la base de datos:", str(e))
            flash(f"Ocurrió un error al registrar tu usuario: {str(e)}", "danger")
    else:
        # Muestra por qué las validaciones fallaron (si aplican)
        print("Errores en la validación del formulario:", form.errors)

    return render_template("registro.html", form=form)

@app.route("/login", methods=["POST", "GET"])
def login():
    form = forms.Login_form()
    print(f"Datos recibidos del formulario: {form.data}")  # Debugging opcional

    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(usuario=form.usuario.data).first()

        if usuario and usuario.check_contrasenya(form.contrasenya.data):
            login_user(usuario)  # Inicia sesión del usuario

            # Verificación del rol del usuario
            if usuario.rol == "admin":  # Asegúrate de que los roles estén configurados en tu modelo
                return redirect(url_for("menu_principal"))  # Ruta para el menú del administrador
            elif usuario.rol == "cliente":
                return redirect(url_for("menu_cliente"))  # Ruta para el menú del cliente
            else:
                flash("Rol de usuario desconocido. Contacte al administrador.", "warning")
                return redirect(url_for("login"))  # Regresa al login si hay un error

        else:
            flash("Usuario o contraseña incorrectos.", "danger")
            print("Mensaje de error enviado.")

    return render_template("index.html", form=form)

@app.route("/logout", methods= ["POST", "GET"])
@login_required
def logout():
    logout_user()
    flash("Has cerrado la sesión  correctamente.", "info")
    return redirect(url_for("login"))

@app.route("/menu_principal", methods=["GET", "POST"])
@login_required
@role_required("admin")
def menu_principal():
    if current_user.is_authenticated and current_user.rol == "admin":
        return render_template("menu.html")
    else:
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for("index"))

@app.route("/menu-cliente", methods=["GET", "POST"])
@login_required
@role_required("cliente")
def menu_cliente():
    if current_user.is_authenticated and current_user.rol == "cliente":  # Verifica que el rol sea Cliente
        return render_template("menu-cliente.html")  # Renderiza el menú del cliente
    else:
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for("index"))  # Redirige a la página de inicio si no cumple con el rol

@app.route("/perfil_cliente", methods=["GET", "POST"])
@login_required
@role_required("cliente")
def perfil_cliente():
    #obtenemos el usuario actual
    usuario = current_user

    # Crear el formulario
    form = EditarPerfilForm()

    # Pre-cargar datos actuales en el formulario
    if request.method == "GET":
        form.nombre_usuario.data = usuario.nombre
        form.direccion.data = usuario.direccion

    # Procesar el formulario
    if form.validate_on_submit():
        # Actualizar los datos del usuario
        usuario.nombre = form.nombre_usuario.data
        usuario.direccion = form.direccion.data

        # Guardar cambios
        try:
            db.session.commit()
            flash("Tu perfil ha sido actualizado con éxito.", "success")
            return redirect(url_for("perfil-cliente"))
        except Exception as e:
            db.session.rollback()
            flash("Error al actualizar el perfil. Inténtalo nuevamente.", "danger")

    return render_template("perfil-cliente.html", form=form, usuario= usuario)

@app.route("/productos", methods=["GET", "POST"])
@login_required
@role_required("admin")
def productos():
    # Obtener todos los productos usando Flask-SQLAlchemy
    productos = Producto.query.all()  # Reemplaza session.query con Producto.query
    print(productos)

    # Renderizar la plantilla con los productos
    return render_template("productos.html", productos=productos)










@app.route("/productos_cliente", methods=["GET", "POST"])
@login_required
@role_required("cliente")
def productos_cliente():
    # Obtener todos los productos usando Flask-SQLAlchemy
    productos = Producto.query.all()
    print(productos)

    # Renderizar la plantilla con los productos
    return render_template("productos-cliente.html", productos=productos)

@app.route('/agregar_a_la_cesta/<producto_id>', methods=['POST'])
@login_required
@role_required("cliente")
def agregar_a_la_cesta(producto_id):
    usuario_id = current_user.id
    item = CestaDeCompra.query.filter_by(usuario_id=usuario_id, producto_id=producto_id).first()

    if item:
        item.cantidad += 1
    else:
        nuevo_item = CestaDeCompra(usuario_id=usuario_id, producto_id=producto_id, cantidad=1)
        db.session.add(nuevo_item)

    db.session.commit()
    return redirect(url_for('productos_cliente'))

@app.route("/cesta", methods=['POST', 'GET'])
@login_required
@role_required("cliente")
def cesta():
    usuario_id = current_user.id
    cesta_items = CestaDeCompra.query.filter_by(usuario_id=usuario_id).all()
    total = 0
    for item in cesta_items:
        total += item.producto.precio * item.cantidad

    return render_template("cesta.html", cesta_items=cesta_items, total=total)

@app.route('/actualizar_cesta/<item_id>', methods=['POST'])
@login_required
@role_required("cliente")
def actualizar_cesta(item_id):
    cantidad = request.form.get('cantidad', type=int)
    item = CestaDeCompra.query.filter_by(id=item_id).first()

    if item and cantidad > 0:
        item.cantidad = cantidad
    elif item and cantidad == 0:
        db.session.delete(item)

    db.session.commit()
    return redirect(url_for('cesta'))

@app.route('/eliminar_de_la_cesta/<item_id>', methods=['POST'])
@login_required
@role_required("cliente")
def eliminar_de_la_cesta(item_id):
    item = CestaDeCompra.query.filter_by(id=item_id).first()

    if item:
        db.session.delete(item)
        db.session.commit()

    return redirect(url_for('cesta'))

@app.route('/realizar_compra', methods=['POST'])
@login_required
@role_required("cliente")
def realizar_compra():
    usuario_id = current_user.id
    cesta_items = CestaDeCompra.query.filter_by(usuario_id=usuario_id).all()

    if not cesta_items:
        flash('No hay productos en la cesta', 'warning')
        return redirect(url_for('cesta'))

    total = 0
    compras = []
    for item in cesta_items:
        producto = item.producto
        proveedor = producto.proveedor
        precio_unitario = producto.precio
        cantidad = item.cantidad
        iva = proveedor.iva  # Asumiendo que cada proveedor tiene un atributo 'iva' que es el porcentaje de IVA
        precio_con_iva = precio_unitario * (1 + iva / 100)
        total_producto = precio_con_iva * cantidad

        compra = Compra(
            producto_id=producto.id,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            proveedor_id=proveedor.id,
            total=total_producto
        )
        compras.append(compra)
        total += total_producto

    # Guardar las compras en la base de datos
    for compra in compras:
        db.session.add(compra)

    # Vaciar la cesta
    for item in cesta_items:
        db.session.delete(item)

    db.session.commit()
    flash('Compra realizada con éxito', 'success')

    return render_template('confirmacion_de_compra.html', compras=compras, total=total)














# Endpoint para obtener los tipos de producto según el proveedor seleccionado
@app.route('/tipos-producto/<proveedor_id>', methods=['GET'])
def obtener_tipos_producto(proveedor_id):
    try:
        # Obtener el proveedor por ID
        proveedor = Proveedor.query.filter_by(id=proveedor_id).first()
        if not proveedor:
            return jsonify({'error': 'Proveedor no encontrado'}), 404

        # Convertir el campo tipo_producto en una lista separada por comas
        tipos_producto = proveedor.tipo_producto.split(',') if proveedor.tipo_producto else []
        return jsonify({'tipos_producto': tipos_producto})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint para obtener la información del proveedor
@app.route('/proveedor/<proveedor_id>', methods=['GET'])
def obtener_proveedor(proveedor_id):
    try:
        # Buscar el proveedor
        proveedor = Proveedor.query.filter_by(id=proveedor_id).first()
        if not proveedor:
            return jsonify({'error': 'Proveedor no encontrado'}), 404

        # Retornar el CIF
        return jsonify({'cif': proveedor.cif})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

MARCAS = {
    'Procesador': ['Intel', 'AMD', 'Qualcomm', 'ARM', 'Apple'],
    'Placa Base': ['Asus', 'Gigabyte', 'MSI', 'ASRock', 'Biostar'],
    'Ordenador': ['HP', 'Dell', 'Lenovo', 'Acer', 'Apple', 'Asus'],
    'Fuente': ['Corsair', 'Seasonic', 'EVGA', 'Thermaltake', 'Cooler Master'],
    'Disco Duro': ['Samsung', 'Seagate', 'Western Digital', 'Toshiba', 'Hitachi'],
    'RAM': ['Kingston', 'Corsair', 'G.Skill', 'Crucial', 'Patriot'],
    'Tarjeta Gráfica': ['NVIDIA', 'AMD', 'ASUS', 'EVGA', 'ZOTAC'],
}

@app.route('/get_marcas', methods=['GET'])
def get_marcas():
    tipo_producto = request.args.get('tipo_producto')  # Obtener el nombre del tipo de producto
    print(f"Tipo de producto recibido: {tipo_producto}")  # Debug
    marcas = MARCAS.get(tipo_producto, [])  # Obtener las marcas o una lista vacía si no existe
    marcas_json = [{'id': idx, 'nombre': marca} for idx, marca in enumerate(marcas)]
    return jsonify(marcas_json)

MARCAS_Y_MODELOS = {
    'Procesador': {
        'Intel': ['Core i9-13900K', 'Core i7-13700K', 'Core i5-13600K', 'Core i3-13100', 'Xeon W9-3495X'],
        'AMD': ['Ryzen 9 7950X', 'Ryzen 7 7800X3D', 'Ryzen 5 7600X', 'Ryzen 3 4100', 'Threadripper PRO 5995WX'],
        'Qualcomm': ['Snapdragon 8cx Gen 3', 'Snapdragon 8 Gen 2', 'Snapdragon 7+ Gen 2', 'Snapdragon 6 Gen 1', 'Snapdragon 888'],
        'ARM': ['Cortex-X4', 'Cortex-A78', 'Cortex-A55', 'Neoverse N2', 'Ethos-N78'],
        'Apple': ['M2 Ultra', 'M2 Max', 'M2 Pro', 'A17 Bionic', 'M3'],
    },
    'Placa Base': {
        'Asus': ['ROG Crosshair X670E Hero', 'TUF Gaming X570-Plus', 'PRIME Z690-P', 'ROG Strix B550-F', 'ProArt Z790-Creator'],
        'Gigabyte': ['Z790 AORUS Master', 'B550 AORUS Elite', 'X670 AORUS Elite AX', 'Z690 GAMING X', 'H610M H'],
        'MSI': ['MPG Z790 Carbon Wi-Fi', 'MAG B550 TOMAHAWK', 'PRO B760-P DDR4', 'MEG X670E ACE', 'H510M-A PRO'],
        'ASRock': ['X670E Taichi', 'B550M Steel Legend', 'Z690 Phantom Gaming 4', 'H570M-ITX', 'A520M-HDV'],
        'Biostar': ['RACING B550GTQ', 'Z790 VALKYRIE', 'A320MH', 'TB360-BTC PRO', 'H81MHV3'],
    },
    'Ordenador': {
        'HP': ['OMEN 45L', 'Pavilion Gaming Desktop', 'Victus 15L', 'EliteDesk 800 G9', 'Z2 G9 Tower'],
        'Dell': ['Alienware Aurora R15', 'XPS Desktop', 'OptiPlex 7000', 'Precision 3660', 'Inspiron 3910'],
        'Lenovo': ['Legion Tower 7i', 'IdeaCentre Gaming 5i', 'ThinkCentre M75q Gen 2', 'Yoga AIO 7', 'ThinkStation P360'],
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
        'Kingston': ['FURY Beast 16GB DDR5', 'HyperX Predator 32GB DDR4', 'ValueRAM 8GB DDR4', 'FURY Renegade 32GB DDR5', 'HyperX Impact 16GB DDR4'],
        'Corsair': ['Vengeance LPX 16GB DDR4', 'Dominator Platinum RGB 32GB DDR5', 'Vengeance RGB Pro 32GB DDR4', 'LPX 8GB DDR4', 'TWINX 16GB DDR3'],
        'G.Skill': ['Trident Z RGB 32GB DDR4', 'Ripjaws V 16GB DDR4', 'Flare X 16GB DDR5', 'Sniper X 8GB DDR4', 'Aegis 32GB DDR4'],
        'Crucial': ['Ballistix 16GB DDR4', 'Crucial DDR5 32GB', 'Crucial DDR4 8GB', 'Ballistix MAX 16GB DDR4', 'Crucial DDR3 16GB'],
        'Patriot': ['Viper Steel 32GB DDR4', 'Viper RGB 16GB DDR4', 'Signature Line 8GB DDR4', 'Viper Elite II 16GB DDR4', 'Viper Venom DDR5 32GB'],
    },
    'Tarjeta Gráfica': {
        'NVIDIA': ['GeForce RTX 4090', 'GeForce RTX 4080 Super', 'GeForce RTX 4070 Ti', 'GeForce RTX 4060 Ti', 'GeForce GTX 1650 Super'],
        'AMD': ['Radeon RX 7900 XTX', 'Radeon RX 7800 XT', 'Radeon RX 7700 XT', 'Radeon RX 7600', 'Radeon RX 6700 XT'],
        'ASUS': ['ROG Strix RTX 4090', 'TUF Gaming RTX 4080', 'Dual RTX 4060', 'ProArt RTX 4070', 'Phoenix GTX 1630'],
        'EVGA': ['EVGA FTW3 RTX 3090', 'EVGA XC3 RTX 3080', 'EVGA SC Ultra RTX 3060', 'EVGA KO RTX 2060', 'EVGA GT 710'],
        'ZOTAC': ['ZOTAC Gaming RTX 4090 AMP Extreme', 'ZOTAC Gaming RTX 4080 Trinity', 'ZOTAC Twin Edge RTX 3060', 'ZOTAC Mini RTX 3050', 'ZOTAC GT 1030'],
    }
}


@app.route("/get_modelos", methods=["GET"])
def get_modelos():
    tipo_producto = request.args.get("tipo_producto")  # Se obtiene el tipo de producto
    marca = request.args.get("marca")  # Se obtiene la marca seleccionada

    if tipo_producto in MARCAS_Y_MODELOS and marca in MARCAS_Y_MODELOS[tipo_producto]:
        modelos = MARCAS_Y_MODELOS[tipo_producto][marca]  # Se obtienen los modelos
        modelos_json = [{"id": idx, "modelo": modelo} for idx, modelo in enumerate(modelos)]
        return jsonify(modelos_json)

    return jsonify({"error": "No hay modelos disponibles"}), 404

@app.route("/agregar-producto", methods=["GET", "POST"])
@login_required
@role_required("admin")
def agregar_producto():
    proveedores = Proveedor.query.all()

    if request.method == "POST":
        try:
            print("Paso 1: Datos del formulario recibidos")
            # Recuperar datos del formulario
            tipo = request.form.get("tipo_producto", "").strip()
            marca = request.form.get("marca", "").strip()
            modelo = request.form.get("modelo", "").strip()
            marca = request.form.get("marca", "").strip()
            num_referencia = request.form.get("num_referencia", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            cantidad = int(request.form.get("cantidad", 0))
            cantidad_minima = int(request.form.get("cantidad_minima", 0))
            precio = float(request.form.get("precio", 0.0))
            proveedor_id = request.form.get("proveedor_id", "").strip()

            print(f"Datos recibidos: tipo={tipo}, marca={marca}, modelo={modelo}, descripcion={descripcion}, cantidad={cantidad}, precio={precio}, proveedor_id={proveedor_id}")

            # Validar que todos los campos requeridos estén presentes
            if not tipo or not marca or not proveedor_id:
                flash("Todos los campos obligatorios deben ser completados.", "error")
                return render_template("agregar-producto.html", proveedores=proveedores)

            # Validar que el proveedor exista
            proveedor = Proveedor.query.filter_by(id=proveedor_id).first()
            if not proveedor:
                flash("El proveedor seleccionado no existe", "error")
                return render_template("agregar-producto.html", proveedores=proveedores)

            print("Paso 2: Validación del proveedor exitosa")

            # Crear y guardar el nuevo producto
            nuevo_producto = Producto(
                proveedor_id=proveedor_id,
                tipo_producto=tipo,
                modelo=modelo,
                descripcion=descripcion,
                cantidad=cantidad,
                cantidad_minima=cantidad_minima,
                precio=precio,
                marca=marca,
                num_referencia=num_referencia
            )
            db.session.add(nuevo_producto)
            db.session.commit()

            print("Paso 3: Producto creado y guardado en la base de datos")

            # Registrar actividad
            registrar_actividad(
                usuario_id=current_user.id,
                accion=f"Se añadió producto: {nuevo_producto.descripcion} con ID {nuevo_producto.id}",
                modulo="Gestión de Productos"
            )

            print("Paso 4: Actividad registrada")

            flash("Producto agregado con éxito", "success")
            return redirect(url_for("productos"))

        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar el producto: {e}")  # Mostrar el error en consola
            flash(f"Error al guardar el producto: {str(e)}", "error")
            return render_template("agregar-producto.html", proveedores=proveedores)

    return render_template("agregar-producto.html", proveedores=proveedores)

@app.route("/editar_producto/<string:id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def editar_producto(id):
    # Buscar el producto por ID
    producto = Producto.query.get_or_404(id)

    # Obtener la información del proveedor relacionado con el producto
    proveedor = Proveedor.query.get(producto.proveedor_id) if producto.proveedor_id else None

    if request.method == "POST":
        # Obtener nuevos valores desde el formulario
        producto.descripcion = request.form["descripcion"]
        producto.cantidad = request.form["cantidad"]
        producto.cantidad_minima = request.form["cantidad_minima"]
        producto.precio = request.form["precio"]
        producto.num_referencia = request.form["num_referencia"]

        # Guardar los cambios en la base de datos
        db.session.commit()

        # Registrar actividad
        registrar_actividad(
            usuario_id=current_user.id,
            accion=f"Editó el producto {producto.id}",
            modulo="Gestión de Productos"
        )

        flash("Producto actualizado correctamente", "success")
        return redirect(url_for("productos"))

    # Renderizar el formulario de edición con el proveedor
    return render_template("editar_producto.html", producto=producto, proveedor=proveedor)

@app.route("/eliminar_producto/<string:id>", methods=["POST"])
@login_required
@role_required("admin")
def eliminar_producto(id):
    #busca el producto por el id
    producto = Producto.query.get_or_404(id)
    if producto:
        #eliminar de la base de datos
        db.session.delete(producto)
        db.session.commit()

        # Registrar actividad
        registrar_actividad(
            usuario_id=current_user.id,
            accion=f"Eliminó el producto {producto.nombre} con ID {producto.id}",
            modulo="Gestión de Productos"
        )

        flash("Producto eliminado correctamente", "success")
        #redireccionar a la lista de productos
        return redirect(url_for("productos"))
    else:
        return "Producto no encontrado", 404

@app.route("/proveedores", methods=["GET", "POST"])
@login_required
@role_required("admin")
def proveedores():
    print("Entrando en /proveedores")
    proveedores = Proveedor.query.all()  # Recuperar todos los proveedores
    print("Datos recuperados:", proveedores)
    return render_template("proveedores.html", proveedores=proveedores)

@app.route('/agregar-proveedor', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def agregar_proveedor():
    """
    Ruta para agregar un nuevo proveedor a la base de datos.
    """
    print(request.form)  # Debug: Ver los datos enviados por el formulario

    if request.method == 'POST':
        # Validar los datos del formulario
        valido, datos_o_error = validar_datos_proveedor(request.form)
        if not valido:
            flash(datos_o_error, 'danger')  # Mostrar el mensaje de error
            return render_template('agregar-proveedor.html', form=ProveedorForm())

        # Intentar guardar los datos en la base de datos
        try:
            nuevo_proveedor = Proveedor(**datos_o_error)  # Crear una instancia del modelo
            db.session.add(nuevo_proveedor)              # Agregar a la sesión
            db.session.commit()                          # Confirmar cambios

            # Registrar actividad
            registrar_actividad(
                usuario_id=current_user.id,
                accion=f"Añadió al Proveedor {nuevo_proveedor.nombre} con ID {nuevo_proveedor.id}",
                modulo="Gestión de Proveedores"
            )

            flash('Proveedor registrado exitosamente.', 'success')
            return redirect('/proveedores')
        except Exception as e:
            db.session.rollback()  # Revertir cambios en caso de error
            app.logger.error(f"Error al guardar proveedor: {str(e)}")  # Registrar el error
            flash(f'Error al guardar el proveedor: {e}', 'danger')

    # Si el método es GET o hay errores, renderizar el formulario
    return render_template('agregar-proveedor.html', form=ProveedorForm())

@app.route('/editar_proveedor/<string:proveedor_id>', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def editar_proveedor(proveedor_id):
    """
    Ruta para editar un proveedor existente.
    """
    # Buscar el proveedor por ID
    proveedor = Proveedor.query.get_or_404(proveedor_id)

    if request.method == 'POST':
        # Validar los datos del formulario
        valido, datos_o_error = validar_datos_proveedor(request.form)
        if not valido:
            flash(datos_o_error, 'danger')  # Mostrar el mensaje de error
            return render_template('editar_proveedor.html', form=ProveedorForm(), proveedor=proveedor)

        try:
            # Actualizar los datos del proveedor
            proveedor.nombre = datos_o_error['nombre']
            proveedor.telefono = datos_o_error['telefono']
            proveedor.direccion = datos_o_error['direccion']
            proveedor.email = datos_o_error['email']
            proveedor.cif = datos_o_error['cif']
            proveedor.tasa_de_descuento = float(datos_o_error['tasa_de_descuento'])
            proveedor.iva = float(datos_o_error['iva'])
            proveedor.tipo_producto = datos_o_error['tipo_producto']

            # Guardar cambios en la base de datos
            db.session.commit()

            # Registrar actividad
            registrar_actividad(
                usuario_id=current_user.id,
                accion=f"Editó el producto {proveedor.nombre} con ID {proveedor.id}",
                modulo="Gestión de Productos"
            )

            flash('Proveedor actualizado exitosamente.', 'success')
            return redirect('/proveedores')
        except Exception as e:
            db.session.rollback()  # Revertir cambios en caso de error
            app.logger.error(f"Error al actualizar proveedor: {str(e)}")  # Registrar el error
            flash(f'Error al actualizar el proveedor: {e}', 'danger')

    # Cargar el formulario con los datos actuales (GET)
    form = ProveedorForm(
        nombre=proveedor.nombre,
        telefono=proveedor.telefono,
        direccion=proveedor.direccion,
        email=proveedor.email,
        cif=proveedor.cif,
        tasa_de_descuento=proveedor.tasa_de_descuento if proveedor.tasa_de_descuento is not None else 0,
        iva=proveedor.iva if proveedor.iva is not None else 0,
        productos=proveedor.tipo_producto.split(", ")  # Convertir a lista para checkboxes
    )
    return render_template('editar_proveedor.html', form=form, proveedor=proveedor)

@app.route("/eliminar_proveedor/<string:id>", methods=["POST"])
@login_required
@role_required("admin")
def eliminar_proveedor(id):
    proveedor = Proveedor.query.get_or_404(id)  # Buscar el proveedor o devolver 404 si no existe
    db.session.delete(proveedor)  # Eliminar el proveedor
    db.session.commit()  # Confirmar la eliminación en la base de datos

    # Registrar actividad
    registrar_actividad(
        usuario_id=current_user.id,
        accion=f"Eliminó el proveedor {proveedor.nombre} con ID {proveedor.id}",
        modulo="Gestión de Proveedores"
    )
    return redirect(url_for("proveedores"))  # Redirigir a la lista de proveedores

@app.route("/graficas", methods=["GET"])
@login_required
@role_required("admin")
def graficas():
    return render_template("graficas.html", graficas= graficas)

@app.route("/graficas_cliente", methods=["GET"])
@login_required
@role_required("cliente")
def graficas_cliente():
    return render_template("graficas-cliente.html", graficas= graficas)

@app.route("/actividades", methods=["POST", "GET"])
def actividades():
    if current_user.rol != "admin":  # Solo admins pueden ver las actividades
        flash("No tienes permiso para acceder a esta página.", "danger")
        return redirect(url_for('index'))

    actividades = ActividadUsuario.query.order_by(ActividadUsuario.fecha.desc()).all()
    usuarios = Usuario.query.order_by(Usuario.fecha_registro.desc()).all()
    return render_template("menu-admin.html", actividades=actividades, usuarios=usuarios)

if __name__ == "__main__":
    with app.app_context():  # Inicia un contexto de aplicación
        db.create_all()  # Crea las tablas en la base de datos
        print("Tablas creadas exitosamente.")
    app.run(debug=True)