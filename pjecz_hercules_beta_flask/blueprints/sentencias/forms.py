"""
Sentencias, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from lib.safe_string import EXPEDIENTE_REGEXP, SENTENCIA_REGEXP
from wtforms import BooleanField, DateField, FileField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp


class SentenciaNewForm(FlaskForm):
    """Formulario para nueva Sentencia"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    sentencia = StringField("Sentencia", validators=[DataRequired(), Length(max=16), Regexp(SENTENCIA_REGEXP)])
    sentencia_fecha = DateField("Fecha de la sentencia", validators=[DataRequired()])
    expediente = StringField("Expediente", validators=[DataRequired(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    fecha = DateField("Fecha de publicación", validators=[DataRequired()])
    materia = SelectField("Materia", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    materia_tipo_juicio = SelectField("Tipo de Juicio", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    descripcion = TextAreaField("Resumen (OPCIONAL)", validators=[Optional(), Length(max=1024)], render_kw={"rows": 6})
    es_perspectiva_genero = BooleanField("Es Perspectiva de Género", validators=[Optional()])
    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    guardar = SubmitField("Guardar")


class SentenciaEditForm(FlaskForm):
    """Formulario para editar Sentencia"""

    sentencia = StringField("Sentencia", validators=[DataRequired(), Length(max=16), Regexp(SENTENCIA_REGEXP)])
    sentencia_fecha = DateField("Fecha de la sentencia", validators=[Optional()])
    expediente = StringField("Expediente", validators=[DataRequired(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    fecha = DateField("Fecha de publicación", validators=[DataRequired()])
    materia = SelectField("Materia", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    materia_tipo_juicio = SelectField("Tipo de Juicio", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    descripcion = TextAreaField("Resumen (OPCIONAL)", validators=[Optional(), Length(max=1024)], render_kw={"rows": 6})
    es_perspectiva_genero = BooleanField("Es Perspectiva de Género", validators=[Optional()])
    guardar = SubmitField("Guardar")
