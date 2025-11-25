import re

from wtforms import PasswordField, DateField, FieldList, FormField
from wtforms.validators import EqualTo, ValidationError
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


def _strong_password(form, field):
    value = field.data or ""
    if not value:
        return
    if len(value) < 8 or not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"[0-9]", value) or not re.search(r"[\W_]", value):
        raise ValidationError(
            "La contraseÃƒÆ’Ã‚Â±a debe tener al menos 8 caracteres, con mayÃƒÆ’Ã‚Âºscula, minÃƒÆ’Ã‚Âºscula, nÃƒÆ’Ã‚Âºmero y sÃƒÆ’Ã‚Â­mbolo."
        )


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
        # Ajustamos la longitud mÃƒÆ’Ã‚Â¡xima para que coincida con la columna
        # (50 caracteres) y evitar truncados en BD.
        validators=[DataRequired(), Length(min=3, max=50)]
    )
    direccion = StringField(
        "Direccion",
        # Se amplÃƒÆ’Ã‚Â­a a 150 para acompaÃƒÆ’Ã‚Â±ar el tamaÃƒÆ’Ã‚Â±o de columna y permitir
        # direcciones mÃƒÆ’Ã‚Â¡s completas.
        validators=[DataRequired(), Length(min=3, max=150)]
    )
    contrasenya = PasswordField(
        "ContraseÃƒÆ’Ã‚Â±a",
        validators=[DataRequired(), _strong_password]
    )
    contrasenya2 = PasswordField(
        'Confirmar ContraseÃƒÆ’Ã‚Â±a',
        validators=[DataRequired(), EqualTo('contrasenya', message='Las contraseÃƒÆ’Ã‚Â±as deben coincidir')]
    )
    registrar = SubmitField("Registrar")

class EditarPerfilForm(FlaskForm):
    nombre_usuario = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=2, max=50)])
    direccion = StringField('DirecciÃƒÆ’Ã‚Â³n', validators=[DataRequired(), Length(min=5, max=100)])
    current_password = PasswordField('ContraseÃƒÆ’Ã‚Â±a actual', validators=[Optional(), Length(min=6, max=128)])
    new_password = PasswordField('Nueva contraseÃƒÆ’Ã‚Â±a', validators=[Optional(), _strong_password])
    new_password2 = PasswordField(
        'Confirmar nueva contraseÃƒÆ’Ã‚Â±a',
        validators=[Optional(), EqualTo('new_password', message='Las contraseÃƒÆ’Ã‚Â±as deben coincidir')]
    )
    currency_locale = SelectField(
        'Idioma/moneda',
        choices=[('es_ES', 'EspaÃƒÆ’Ã‚Â±ol (ES)'), ('en_US', 'InglÃƒÆ’Ã‚Â©s (US)'), ('en_GB', 'InglÃƒÆ’Ã‚Â©s (GB)')],
        validators=[Optional()]
    )
    submit = SubmitField('Guardar Cambios')

class Login_form(FlaskForm):
    usuario = StringField(
        "Usuario",
        # Se alinea el mÃƒÆ’Ã‚Â¡ximo con la columna de usuario (50 caracteres).
        validators=[
            DataRequired(message="El nombre de usuario es obligatorio."),
            Length(min=3, max=50, message="El nombre de usuario debe tener entre 3 y 50 caracteres.")
        ]
    )
    contrasenya = PasswordField(
        "Contrasenya",
        validators=[
            DataRequired(message="La contraseÃƒÆ’Ã‚Â±a es obligatoria.")
        ]
    )
    submit = SubmitField("Iniciar sesiÃƒÆ’Ã‚Â³n")

class Registro_producto(FlaskForm):
    nombre = StringField(
        "Nombre del Producto",
        validators=[
            DataRequired(message="El nombre es obligatorio."),
            Length(min=3, max=100, message="El nombre debe tener entre 3 y 100 caracteres.")
        ]
    )
    descripcion = TextAreaField(
        "DescripciÃƒÆ’Ã‚Â³n",
        validators=[
            Optional(),  # No es obligatorio
            Length(max=500, message="La descripciÃƒÆ’Ã‚Â³n no debe exceder los 500 caracteres.")
        ]
    )
    cantidad = IntegerField(
        "Cantidad",
        validators=[
            DataRequired(message="La cantidad es obligatoria."),
            NumberRange(min=0, message="La cantidad debe ser un nÃƒÆ’Ã‚Âºmero positivo.")
        ]
    )
    cantidad_minima = IntegerField(
        "Cantidad mÃƒÆ’Ã‚Â­nima",
        validators=[
            DataRequired(message="La cantidad mÃƒÆ’Ã‚Â­nima es obligatoria."),
            NumberRange(min=0, message="La cantidad mÃƒÆ’Ã‚Â­nima debe ser un nÃƒÆ’Ã‚Âºmero positivo.")
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
        choices=[],  # Se llenarÃƒÆ’Ã‚Â¡ dinÃƒÆ’Ã‚Â¡micamente
        validators=[
            DataRequired(message="La marca es obligatoria.")
        ],
        render_kw = {"id": "marca"}
    )
    num_referencia = StringField(
        "NÃƒÆ’Ã‚Âºmero de referencia",
        validators=[
            DataRequired(message="El nÃƒÆ’Ã‚Âºmero de referencia es obligatorio."),
            Length(min=3, max=50, message="El nÃƒÆ’Ã‚Âºmero de referencia debe tener entre 3 y 50 caracteres.")
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
        'TelÃƒÆ’Ã‚Â©fono',
        validators=[
            DataRequired(message="El telÃƒÆ’Ã‚Â©fono es obligatorio."),
            Regexp(r'^\d{9,15}$', message="El telÃƒÆ’Ã‚Â©fono debe contener entre 9 y 15 dÃƒÆ’Ã‚Â­gitos.")
        ]
    )
    direccion = StringField(
        'DirecciÃƒÆ’Ã‚Â³n',
        validators=[
            DataRequired(message="La direcciÃƒÆ’Ã‚Â³n es obligatoria."),
            Length(max=255, message="La direcciÃƒÆ’Ã‚Â³n no debe exceder los 255 caracteres.")
        ]
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(message="El correo electrÃƒÆ’Ã‚Â³nico es obligatorio."),
            Email(message="Ingrese un correo electrÃƒÆ’Ã‚Â³nico vÃƒÆ’Ã‚Â¡lido."),
            Length(max=255, message="El correo electrÃƒÆ’Ã‚Â³nico no debe exceder los 255 caracteres.")
        ]
    )
    cif = StringField(
        'CIF',
        validators=[
            DataRequired(message="El CIF es obligatorio."),
            Regexp(r'^[A-Za-z0-9]{9}$', message="El CIF debe contener 9 caracteres alfanumÃƒÆ’Ã‚Â©ricos.")
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
    """Formulario liviano para validar altas de producto vÃƒÆ’Ã‚Â­a WTForms.

    Se deshabilita el CSRF en la vista que lo consume para poder reutilizar las
    plantillas existentes sin romperlas, pero mantenemos validaciones de
    longitud y rango para bloquear datos invÃƒÆ’Ã‚Â¡lidos antes de tocar la BD.
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
        'DescripciÃƒÆ’Ã‚Â³n', validators=[Optional(), Length(max=500)]
    )
    cantidad = IntegerField(
        'Cantidad', validators=[DataRequired(), NumberRange(min=0)]
    )
    cantidad_minima = IntegerField(
        'Cantidad mÃƒÆ’Ã‚Â­nima', validators=[Optional(), NumberRange(min=0)]
    )
    precio = DecimalField(
        'Precio', validators=[DataRequired(), NumberRange(min=0.01)]
    )
    costo = DecimalField(
        'Costo', validators=[DataRequired(), NumberRange(min=0.00)]
    )
    num_referencia = StringField(
        'NÃƒÆ’Ã‚Âºmero de referencia', validators=[DataRequired(), Length(max=80)]
    )
    proveedor_id = StringField(
        'Proveedor', validators=[DataRequired(), Length(max=8)]
    )


# --- Formularios de Contabilidad ---

class ApunteForm(FlaskForm):
    cuenta_codigo = StringField('CÃƒÆ’Ã‚Â³digo Cuenta', validators=[DataRequired()])
    debe = DecimalField('Debe', default=0.00, validators=[NumberRange(min=0)])
    haber = DecimalField('Haber', default=0.00, validators=[NumberRange(min=0)])

class AsientoManualForm(FlaskForm):
    descripcion = StringField('DescripciÃƒÆ’Ã‚Â³n', validators=[DataRequired(), Length(max=255)])
    fecha = DateField('Fecha', format='%Y-%m-%d', validators=[Optional()])
    # Usamos FieldList para permitir mÃƒÆ’Ã‚Âºltiples apuntes.
    # En el frontend se puede usar JS para duplicar campos.
    # Inicializamos con 2 apuntes mÃƒÆ’Ã‚Â­nimos para partida doble.
    apuntes = FieldList(FormField(ApunteForm), min_entries=2, max_entries=10)
    submit = SubmitField('Crear Asiento')
