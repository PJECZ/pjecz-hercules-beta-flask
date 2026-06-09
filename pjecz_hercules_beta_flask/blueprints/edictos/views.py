"""
Edictos, vistas
"""

import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.edictos.models import Edicto
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import (
    safe_clave,
    safe_expediente,
    safe_message,
    safe_numero_publicacion,
    safe_string,
)

MODULO = "EDICTOS"

edictos = Blueprint("edictos", __name__, template_folder="templates")


@edictos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@edictos.route("/edictos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Edictos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Edicto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Edicto.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Edicto.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Edicto.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Edicto.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Edicto.expediente == expediente)
        except IndexError, ValueError:
            pass
    if "numero_publicacion" in request.form:
        try:
            numero_publicacion = safe_numero_publicacion(request.form["numero_publicacion"])
            consulta = consulta.filter(Edicto.numero_publicacion == numero_publicacion)
        except IndexError, ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Edicto.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                    "autoridad_clave": resultado.autoridad.clave,
                    "detalle": {
                        "descripcion": resultado.descripcion,
                        "url": url_for("edictos.detail", edicto_id=resultado.id),
                    },
                    "expediente": resultado.expediente,
                    "numero_publicacion": resultado.numero_publicacion,
                    "es_declaracion_de_ausencia": "Sí" if resultado.es_declaracion_de_ausencia else "",
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@edictos.route("/edictos")
def list_active():
    """Listado de Edictos activos"""
    filtros = None
    titulo = None
    mostrar_filtro_autoridad_clave = True
    # Si es administrador
    plantilla = "edictos/list.jinja2"
    if current_user.can_admin(MODULO):
        plantilla = "edictos/list_admin.jinja2"
    # Si viene autoridad_id o autoridad_clave en la URL, agregar a los filtros
    autoridad = None
    if "autoridad_id" in request.args and request.args.get("autoridad_id") is not None:
        autoridad = Autoridad.query.get(request.args.get("autoridad_id"))
    elif "autoridad_clave" in request.args:
        autoridad_clave = safe_clave(request.args.get("autoridad_clave"))
        autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    if autoridad is not None:
        filtros = {"estatus": "A", "autoridad_id": autoridad.id}
        titulo = f"Edictos de {autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False
    # Si es administrador
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todos los Edictos"
        filtros = {"estatus": "A"}
    # Si puede editar o crear, solo ve lo de su autoridad
    if titulo is None and (current_user.can_insert(MODULO) or current_user.can_edit(MODULO)):
        filtros = {"estatus": "A", "autoridad_id": current_user.autoridad.id}
        titulo = f"Edictos de {current_user.autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False
    # De lo contrario, es observador
    if titulo is None:
        filtros = {"estatus": "A"}
        titulo = "Edictos"
    # Entregar
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps(filtros),
        titulo=titulo,
        mostrar_filtro_autoridad_clave=mostrar_filtro_autoridad_clave,
        estatus="A",
    )


@edictos.route("/edictos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Edictos inactivos"""
    return render_template(
        "edictos/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Edictos inactivos",
    )


@edictos.route("/edictos/<int:edicto_id>")
def detail(edicto_id):
    """Detalle de un Edicto"""
    edicto = Edicto.query.get_or_404(edicto_id)
    return render_template("edictos/detail.jinja2", edicto=edicto)


@edictos.route("/edictos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir Edicto como juzgado"""


@edictos.route("/edictos/nuevo/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_with_autoridad_id(autoridad_id):
    """Subir Edicto para una autoridad como administrador"""


@edictos.route("/edictos/editar/<int:edicto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(edicto_id):
    """Editar Edicto"""


@edictos.route("/edictos/eliminar/<int:edicto_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(edicto_id):
    """Eliminar Edicto"""


@edictos.route("/edictos/recuperar/<int:edicto_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(edicto_id):
    """Recuperar Edicto"""


@edictos.route("/edictos/ver_archivo_pdf/<int:edicto_id>")
def view_file_pdf(edicto_id):
    """Ver archivo PDF de Edicto para insertarlo en un iframe en el detalle"""


@edictos.route("/edictos/descargar_archivo_pdf/<int:edicto_id>")
def download_file_pdf(edicto_id):
    """Descargar archivo PDF de Edicto"""
