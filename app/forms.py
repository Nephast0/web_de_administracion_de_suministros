from wtforms import PasswordField, DateField, FieldList, FormField
from wtforms.validators import EqualTo
from wtforms.validators import Email, Regexp
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    IntegerField,
    DecimalField,
    SelectField,
    SelectMultipleField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from wtforms.widgets import CheckboxInput, ListWidget


class MultiCheckboxField(SelectMultipleField):
    """Render a SelectMultipleField as a list of checkboxes."""

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class Formulario_de_registro(FlaskForm):
    nombre= StringField(
        "Nombre",
        validators= [DataRequired()]
    )
    usuario = StringField(
        "Usuario",
        # Ajustamos la longitud máxima para que coincida con la columna
        # (50 caracteres) y evitar truncados en BD.
        validators=[DataRequired(), Length(min=3, max=50)]
    )
    direccion = StringField(
        "Direccion",
        # Se amplía a 150 para acompañar el tamaño de columna y permitir
        # direcciones más completas.
        validators=[DataRequired(), Length(min=3, max=150)]
    )
    contrasenya = PasswordField(
        "Contraseña",
        validators=[DataRequired()]
    )
    contrasenya2 = PasswordField(
        'Confirmar Contraseña',
        validators=[DataRequired(), EqualTo('contrasenya', message='Las contraseñas deben coincidir')]
    )
    registrar = SubmitField("Registrar")

class EditarPerfilForm(FlaskForm):
    nombre_usuario = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=2, max=50)])
    direccion = StringField('Dirección', validators=[DataRequired(), Length(min=5, max=100)])
    submit = SubmitField('Guardar Cambios')

class Login_form(FlaskForm):
    usuario = StringField(
        "Usuario",
        # Se alinea el máximo con la columna de usuario (50 caracteres).
        validators=[
            DataRequired(message="El nombre de usuario es obligatorio."),
            Length(min=3, max=50, message="El nombre de usuario debe tener entre 3 y 50 caracteres.")
        ]
    )
    contrasenya = PasswordField(
        "Contrasenya",
        validators=[
            DataRequired(message="La contraseña es obligatoria.")
        ]
    )
    submit = SubmitField("Iniciar sesión")

class Registro_producto(FlaskForm):
    nombre = StringField(
        "Nombre del Producto",
        validators=[
            DataRequired(message="El nombre es obligatorio."),
            Length(min=3, max=100, message="El nombre debe tener entre 3 y 100 caracteres.")
        ]
    )
    descripcion = TextAreaField(
        "Descripción",
        validators=[
            Optional(),  # No es obligatorio
            Length(max=500, message="La descripción no debe exceder los 500 caracteres.")
        ]
    )
    cantidad = IntegerField(
        "Cantidad",
        validators=[
            DataRequired(message="La cantidad es obligatoria."),
            NumberRange(min=0, message="La cantidad debe ser un número positivo.")
        ]
    )
    cantidad_minima = IntegerField(
        "Cantidad mínima",
        validators=[
            DataRequired(message="La cantidad mínima es obligatoria."),
            NumberRange(min=0, message="La cantidad mínima debe ser un número positivo.")
        ]
    )
    precio = DecimalField(
        "Precio",
        validators=[
            DataRequired(message="El precio es obligatorio."),
            NumberRange(min=0.01, message="El precio debe ser mayor a 0.")
        ]
    )
    tipo_producto = SelectField(
        "Tipo de Producto",
        choices=[
            ('Procesador', 'Procesador'),
            ('Placa Base', 'Placa Base'),
            ('Ordenador', 'Ordenador'),
            ('Fuente', 'Fuente'),
            ('Disco Duro', 'Disco Duro'),
            ('RAM', 'RAM')
        ],
        validators=[
            DataRequired(message="El tipo de producto es obligatorio.")
        ],
        render_kw={"id": "tipo_producto"}
    )
    marca = SelectField(
        "Marca",
        choices=[],  # Se llenará dinámicamente
        validators=[
            DataRequired(message="La marca es obligatoria.")
        ],
        render_kw = {"id": "marca"}
    )
    num_referencia = StringField(
        "Número de referencia",
        validators=[
            DataRequired(message="El número de referencia es obligatorio."),
            Length(min=3, max=50, message="El número de referencia debe tener entre 3 y 50 caracteres.")
        ]
    )
    submit = SubmitField("Agregar Producto")


class ProveedorForm(FlaskForm):
    nombre = StringField(
        'Nombre',
        validators=[
            DataRequired(message="El nombre es obligatorio."),
            Length(max=100, message="El nombre no debe exceder los 100 caracteres.")
        ]
    )
    telefono = StringField(
        'Teléfono',
        validators=[
            DataRequired(message="El teléfono es obligatorio."),
            Regexp(r'^\d{9,15}$', message="El teléfono debe contener entre 9 y 15 dígitos.")
        ]
    )
    direccion = StringField(
        'Dirección',
        validators=[
            DataRequired(message="La dirección es obligatoria."),
            Length(max=255, message="La dirección no debe exceder los 255 caracteres.")
        ]
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(message="El correo electrónico es obligatorio."),
            Email(message="Ingrese un correo electrónico válido."),
            Length(max=255, message="El correo electrónico no debe exceder los 255 caracteres.")
        ]
    )
    cif = StringField(
        'CIF',
        validators=[
            DataRequired(message="El CIF es obligatorio."),
            Regexp(r'^[A-Za-z0-9]{9}$', message="El CIF debe contener 9 caracteres alfanuméricos.")
        ]
    )
    tasa_de_descuento = DecimalField(
        'Tasa de descuento',
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message="La tasa de descuento debe estar entre 0 y 100.")
        ]
    )
    iva = DecimalField(
        'IVA',
        validators=[
            DataRequired(message="El IVA es obligatorio."),
            NumberRange(min=0, max=100, message="El IVA debe estar entre 0 y 100.")
        ]
    )
    productos = MultiCheckboxField(
        'Tipos de productos ofrecidos',
        choices=[],
        validators=[Optional()],
    )


class AgregarProductoForm(FlaskForm):
    """Formulario liviano para validar altas de producto vía WTForms.

    Se deshabilita el CSRF en la vista que lo consume para poder reutilizar las
    plantillas existentes sin romperlas, pero mantenemos validaciones de
    longitud y rango para bloquear datos inválidos antes de tocar la BD.
    """

    tipo_producto = StringField(
        'Tipo de producto',
        validators=[DataRequired(), Length(max=100)],
    )
    marca = StringField(
        'Marca',
        validators=[DataRequired(), Length(max=100)],
    )
    modelo = StringField(
        'Modelo',
        validators=[DataRequired(), Length(max=120)],
    )
    descripcion = TextAreaField(
        'Descripción', validators=[Optional(), Length(max=500)]
    )
    cantidad = IntegerField(
        'Cantidad', validators=[DataRequired(), NumberRange(min=0)]
    )
    cantidad_minima = IntegerField(
        'Cantidad mínima', validators=[Optional(), NumberRange(min=0)]
    )
    precio = DecimalField(
        'Precio', validators=[DataRequired(), NumberRange(min=0.01)]
    )
    costo = DecimalField(
        'Costo', validators=[DataRequired(), NumberRange(min=0.00)]
    )
    num_referencia = StringField(
        'Número de referencia', validators=[DataRequired(), Length(max=80)]
    )
    proveedor_id = StringField(
        'Proveedor', validators=[DataRequired(), Length(max=8)]
    )


# --- Formularios de Contabilidad ---

class ApunteForm(FlaskForm):
    cuenta_codigo = StringField('Código Cuenta', validators=[DataRequired()])
    debe = DecimalField('Debe', default=0.00, validators=[NumberRange(min=0)])
    haber = DecimalField('Haber', default=0.00, validators=[NumberRange(min=0)])

class AsientoManualForm(FlaskForm):
    descripcion = StringField('Descripción', validators=[DataRequired(), Length(max=255)])
    fecha = DateField('Fecha', format='%Y-%m-%d', validators=[Optional()])
    # Usamos FieldList para permitir múltiples apuntes.
    # En el frontend se puede usar JS para duplicar campos.
    # Inicializamos con 2 apuntes mínimos para partida doble.
    apuntes = FieldList(FormField(ApunteForm), min_entries=2, max_entries=10)
    submit = SubmitField('Crear Asiento')
