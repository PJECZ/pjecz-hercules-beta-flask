"""
Estrados, vistas
"""

import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.estrados.models import Estrado
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "ESTRADOS"

estrados = Blueprint("estrados", __name__, template_folder="templates")


@estrados.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@estrados.route("/estrados/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Estrados"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Estrado.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Estrado.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Estrado.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Estrado.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Estrado.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(Estrado.id.desc()).offset(start).limit(rows_per_page).all()
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
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@estrados.route("/estrados")
def list_active():
    """Listado de Estrados activos"""
    filtros = None
    titulo = None
    mostrar_filtro_autoridad_clave = True
    # Si es administrador
    plantilla = "estrados/list.jinja2"
    if current_user.can_admin(MODULO):
        plantilla = "estrados/list_admin.jinja2"
    # Si viene autoridad_id o autoridad_clave en la URL, agregar a los filtros
    autoridad = None
    if "autoridad_id" in request.args and request.args.get("autoridad_id") is not None:
        autoridad = Autoridad.query.get(request.args.get("autoridad_id"))
    elif "autoridad_clave" in request.args:
        autoridad_clave = safe_clave(request.args.get("autoridad_clave"))
        autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    if autoridad is not None:
        filtros = {"estatus": "A", "autoridad_id": autoridad.id}
        titulo = f"Estrados de {autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False
    # Si es administrador
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todos los Estrados"
        filtros = {"estatus": "A"}
    # Si puede editar o crear, solo ve lo de su autoridad
    if titulo is None and (current_user.can_insert(MODULO) or current_user.can_edit(MODULO)):
        filtros = {"estatus": "A", "autoridad_id": current_user.autoridad.id}
        titulo = f"Estrados de {current_user.autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False
    # De lo contrario, es observador
    if titulo is None:
        filtros = {"estatus": "A"}
        titulo = "Estrados"
    # Entregar
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps(filtros),
        titulo=titulo,
        mostrar_filtro_autoridad_clave=mostrar_filtro_autoridad_clave,
        estatus="A",
    )


@estrados.route("/estrados/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Estrados inactivos"""
    return render_template(
        "estrados/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Estrados inactivos",
    )


@estrados.route("/estrados/<int:estrado_id>")
def detail(estrado_id):
    """Detalle de un Estrado"""
    estrado = Estrado.query.get_or_404(estrado_id)
    return render_template("estrados/detail.jinja2", estrado=estrado)
