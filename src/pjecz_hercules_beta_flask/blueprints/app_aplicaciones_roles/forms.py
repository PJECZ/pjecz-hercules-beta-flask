"""
App Aplicaciones Roles, formularios
"""

from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from pjecz_hercules_beta_flask.blueprints.app_aplicaciones_roles.models import AppAplicacionRol
from pjecz_hercules_beta_flask.blueprints.roles.models import Rol

NIVELES = [(nivel, f"{nivel}) {descripcion}") for nivel, descripcion in AppAplicacionRol.NIVELES.items()]


class AppAplicacionRolWithAppAplicacionForm(FlaskForm):
    """Formulario para agregar un rol a una App Aplicación"""

    app_aplicacion_clave = StringField("Aplicación")  # Solo lectura
    rol = SelectField("Rol", coerce=int, validators=[DataRequired()])
    nivel = RadioField("Nivel", coerce=int, choices=NIVELES, validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en rol"""
        super().__init__(*args, **kwargs)
        self.rol.choices = [(r.id, r.nombre) for r in Rol.query.filter_by(estatus="A").order_by(Rol.nombre).all()]


class AppAplicacionRolEditForm(FlaskForm):
    """Formulario para editar el nivel de un App Aplicación Rol"""

    app_aplicacion_clave = StringField("Aplicación")  # Solo lectura
    rol_nombre = StringField("Rol")  # Solo lectura
    nivel = RadioField("Nivel", coerce=int, choices=NIVELES, validators=[DataRequired()])
    guardar = SubmitField("Guardar")
