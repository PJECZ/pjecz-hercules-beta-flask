"""
Sentencias, vistas
"""

import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.materias_tipos_juicios.models import MateriaTipoJuicio
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.sentencias.models import Sentencia
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_expediente, safe_message, safe_sentencia, safe_string

MODULO = "SENTENCIAS"

sentencias = Blueprint("sentencias", __name__, template_folder="templates")


@sentencias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@sentencias.route("/sentencias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Sentencias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Sentencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Sentencia.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Sentencia.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Sentencia.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "materia_tipo_juicio_id" in request.form:
        materia_tipo_juicio = MateriaTipoJuicio.query.get(request.form["materia_tipo_juicio_id"])
        if materia_tipo_juicio:
            consulta = consulta.filter(Sentencia.materia_tipo_juicio_id == materia_tipo_juicio.id)
    elif "materia_tipo_juicio_descripcion" in request.form:
        materia_tipo_juicio_descripcion = safe_string(request.form["materia_tipo_juicio_descripcion"], save_enie=True)
        if materia_tipo_juicio_descripcion != "":
            consulta = consulta.join(MateriaTipoJuicio).filter(
                MateriaTipoJuicio.descripcion.contains(materia_tipo_juicio_descripcion)
            )
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Sentencia.descripcion.contains(descripcion))
    if "sentencia" in request.form:
        try:
            sentencia = safe_sentencia(request.form["sentencia"])
            consulta = consulta.filter(Sentencia.sentencia == sentencia)
        except IndexError, ValueError:
            pass
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Sentencia.expediente == expediente)
        except IndexError, ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Sentencia.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "autoridad_clave": resultado.autoridad.clave,
                "detalle": {
                    "sentencia": resultado.sentencia,
                    "url": url_for("sentencias.detail", sentencia_id=resultado.id),
                },
                "expediente": resultado.expediente,
                "materia_nombre": resultado.materia_tipo_juicio.materia.nombre,
                "materia_tipo_juicio_descripcion": resultado.materia_tipo_juicio.descripcion,
                "descripcion": resultado.descripcion if len(resultado.descripcion) < 48 else resultado.descripcion[:48] + "…",
                "es_perspectiva_genero": "Sí" if resultado.es_perspectiva_genero else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@sentencias.route("/sentencias")
def list_active():
    """Listado de Sentencias activos"""
    filtros = None
    titulo = None
    mostrar_filtro_autoridad_clave = True
    # Si es administrador
    plantilla = "sentencias/list.jinja2"
    if current_user.can_admin(MODULO):
        plantilla = "sentencias/list_admin.jinja2"
    # Si viene autoridad_id o autoridad_clave en la URL, agregar a los filtros
    autoridad = None
    if "autoridad_id" in request.args and request.args.get("autoridad_id") is not None:
        autoridad = Autoridad.query.get(request.args.get("autoridad_id"))
    elif "autoridad_clave" in request.args:
        autoridad_clave = safe_clave(request.args.get("autoridad_clave"))
        autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    if autoridad is not None:
        filtros = {"estatus": "A", "autoridad_id": autoridad.id}
        titulo = f"Glosas de {autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False
    # Si viene materia_tipo_juicio_id en la URL, agregar a los filtros
    materia_tipo_juicio = None
    if "materia_tipo_juicio_id" in request.args and request.args.get("materia_tipo_juicio_id") is not None:
        materia_tipo_juicio = MateriaTipoJuicio.query.get(request.args.get("materia_tipo_juicio_id"))
    if materia_tipo_juicio is not None:
        filtros = {"estatus": "A", "materia_tipo_juicio_id": materia_tipo_juicio.id}
        titulo = f"Listas de Acuerdos de {materia_tipo_juicio.descripcion}"
    # Si es administrador
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todos los Glosas"
        filtros = {"estatus": "A"}
    # Si puede editar o crear, solo ve lo de su autoridad
    if titulo is None and (current_user.can_insert(MODULO) or current_user.can_edit(MODULO)):
        filtros = {"estatus": "A", "autoridad_id": current_user.autoridad.id}
        titulo = f"Glosas de {current_user.autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False
    # De lo contrario, es observador
    if titulo is None:
        filtros = {"estatus": "A"}
        titulo = "Glosas"
    # Entregar
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps(filtros),
        titulo=titulo,
        mostrar_filtro_autoridad_clave=mostrar_filtro_autoridad_clave,
        estatus="A",
    )


@sentencias.route("/sentencias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Senetncias inactivos"""
    return render_template(
        "sentencias/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Senetncias inactivos",
    )


@sentencias.route("/sentencias/<int:sentencia_id>")
def detail(sentencia_id):
    """Detalle de un Sentencia"""
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    return render_template("sentencias/detail.jinja2", sentencia=sentencia)


@sentencias.route("/sentencias/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir Sentencia como juzgado"""


@sentencias.route("/sentencias/nuevo/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_with_autoridad_id(autoridad_id):
    """Subir Sentencia para una autoridad como administrador"""


@sentencias.route("/sentencias/editar/<int:sentencia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(sentencia_id):
    """Editar Sentencia"""


@sentencias.route("/sentencias/eliminar/<int:sentencia_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(sentencia_id):
    """Eliminar Sentencia"""


@sentencias.route("/sentencias/recuperar/<int:sentencia_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(sentencia_id):
    """Recuperar Sentencia"""


@sentencias.route("/sentencias/ver_archivo_pdf/<int:sentencia_id>")
def view_file_pdf(sentencia_id):
    """Ver archivo PDF de una Sentencia para insertarlo en un iframe en el detalle"""


@sentencias.route("/sentencias/descargar_archivo_pdf/<int:sentencia_id>")
def download_file_pdf(sentencia_id):
    """Descargar archivo PDF de una Sentencia"""
