from wtforms import PasswordField
from wtforms.validators import EqualTo
from wtforms.validators import Email, Regexp
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class Formulario_de_registro(FlaskForm):
    nombre= StringField(
        "Nombre",
        validators= [DataRequired()]
    )
    usuario = StringField(
        "Usuario",
        validators=[DataRequired(), Length(min=3, max=100)]
    )
    direccion = StringField(
        "Direccion",
        validators=[DataRequired(), Length(min=3, max=100)]
    )
    contrasenya = PasswordField(
        "Contraseña",
        validators=[DataRequired()]
    )
    contrasenya2 = PasswordField(
        'Confirmar Contraseña',
        validators=[DataRequired(), EqualTo('contrasenya', message='Las contraseñas deben coincidir')]
    )
    rol = SelectField(
        "Rol",
        choices=[("cliente", "Cliente"), ("admin", "Admin")],
        validators=[DataRequired()]
    )
    registrar = SubmitField("Registrar")

class EditarPerfilForm(FlaskForm):
    nombre_usuario = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=2, max=50)])
    direccion = StringField('Dirección', validators=[DataRequired(), Length(min=5, max=100)])
    submit = SubmitField('Guardar Cambios')

class Login_form(FlaskForm):
    usuario = StringField(
        "Usuario",
        validators=[
            DataRequired(message="El nombre de usuario es obligatorio."),
            Length(min=3, max=20, message="El nombre de usuario debe tener entre 3 y 20 caracteres.")
        ]
    )
    contrasenya = PasswordField(
        "Contraseña",
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
    precio = FloatField(
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
    tasa_de_descuento = FloatField(
        'Tasa de descuento',
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message="La tasa de descuento debe estar entre 0 y 100.")
        ]
    )
    iva = FloatField(
        'IVA',
        validators=[
            DataRequired(message="El IVA es obligatorio."),
            NumberRange(min=0, max=100, message="El IVA debe estar entre 0 y 100.")
        ]
    )