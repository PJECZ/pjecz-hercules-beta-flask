"""
Listas de Acuerdos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import DateField, FileField, StringField, SubmitField
from wtforms.validators import DataRequired


class ListaDeAcuerdoNewForm(FlaskForm):
    """Formulario ListaDeAcuerdo para un Juzgado con una Materia"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    fecha = DateField("Fecha (si ya existe otra con la misma fecha, será reemplazada)", validators=[DataRequired()])
    archivo = FileField("Archivo PDF con la Lista de Acuerdos", validators=[FileRequired()])
    guardar = SubmitField("Guardar")


class ListaDeAcuerdoMateriaNewForm(FlaskForm):
    """Formulario ListaDeAcuerdo para un Juzgado que puede seleccionar la Materia"""

    fecha = DateField("Fecha (si ya existe otra con la misma fecha, será reemplazada)", validators=[DataRequired()])
    archivo = FileField("Archivo PDF con la Lista de Acuerdos", validators=[FileRequired()])
    guardar = SubmitField("Guardar")
