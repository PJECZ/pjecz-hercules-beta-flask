"""
Glosas, vistas
"""

import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.glosas.models import Glosa
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_expediente, safe_message, safe_string, safe_uuid

MODULO = "GLOSAS"

glosas = Blueprint("glosas", __name__, template_folder="templates")


@glosas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@glosas.route("/glosas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Glosas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Glosa.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Glosa.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Glosa.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Glosa.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Glosa.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Glosa.expediente == expediente)
        except IndexError, ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Glosa.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "autoridad_clave": resultado.autoridad.clave,
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("glosas.detail", glosa_id=resultado.id),
                },
                "expediente": resultado.expediente,
                "tipo_juicio": resultado.tipo_juicio,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@glosas.route("/glosas")
def list_active():
    """Listado de Glosas activos"""
    filtros = None
    titulo = None
    mostrar_filtro_autoridad_clave = True
    # Si es administrador
    plantilla = "glosas/list.jinja2"
    if current_user.can_admin(MODULO):
        plantilla = "glosas/list_admin.jinja2"
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


@glosas.route("/glosas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Glosas inactivos"""
    return render_template(
        "glosas/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Glosas inactivos",
    )


@glosas.route("/glosas/<int:glosa_id>")
def detail(glosa_id):
    """Detalle de un Glosa"""
    glosa = Glosa.query.get_or_404(glosa_id)
    return render_template("glosas/detail.jinja2", glosa=glosa)


@glosas.route("/glosas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir Glosa como Juzgado"""


@glosas.route("/glosas/nuevo_con_autoridad_id/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_with_autoridad_id(autoridad_id):
    """Subir Glosa para una autoridad como administrador"""


@glosas.route("/glosas/editar/<int:glosa_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(glosa_id):
    """Editar Glosa"""


@glosas.route("/glosas/eliminar/<int:glosa_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(glosa_id):
    """Eliminar Glosa"""


@glosas.route("/glosas/recuperar/<int:glosa_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(glosa_id):
    """Recuperar Glosa"""


@glosas.route("/glosas/ver_archivo_pdf/<int:glosa_id>")
def view_file_pdf(glosa_id):
    """Ver archivo PDF de Glosa para insertarlo en un iframe en el detalle"""


@glosas.route("/glosas/descargar_archivo_pdf/<int:glosa_id>")
def download_file_pdf(glosa_id):
    """Descargar archivo PDF de Glosa"""
