"""
App Aplicaciones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange


class AppAplicacionForm(FlaskForm):
    """Formulario AppAplicacion"""

    clave = StringField("Clave (única, hasta 16 caracteres)", validators=[DataRequired(), Length(max=16)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    cuota_diaria = IntegerField("Cuota diaria (0 = sin acceso)", validators=[InputRequired(), NumberRange(min=0)], default=1000)
    cuota_por_hora = IntegerField("Cuota por hora (0 = sin acceso)", validators=[InputRequired(), NumberRange(min=0)], default=100)
    guardar = SubmitField("Guardar")
