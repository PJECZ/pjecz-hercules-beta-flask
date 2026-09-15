"""
DGT Digitalizaciones, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.dgt_digitalizaciones.models import DgtDigitalizacion
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_string, safe_uuid

MODULO = "DGT DIGITALIZACIONES"

dgt_digitalizaciones = Blueprint("dgt_digitalizaciones", __name__, template_folder="templates")


@dgt_digitalizaciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_digitalizaciones.route("/dgt_digitalizaciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Digitalizaciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtDigitalizacion.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "expediente" in request.form:
        expediente = safe_string(request.form["expediente"])
        if expediente != "":
            consulta = consulta.filter(DgtDigitalizacion.expediente.contains(expediente))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(DgtDigitalizacion.descripcion.contains(descripcion))
    # Luego filtrar por columnas de otras tablas
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(DgtDigitalizacion.archivo_actualizado).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "archivo_nombre": resultado.archivo_nombre,
                    "url": url_for("dgt_digitalizaciones.detail", dgt_digitalizacion_id=resultado.id),
                },
                "autoridad_clave": resultado.autoridad.clave,
                "expediente": resultado.expediente,
                "descripcion": resultado.descripcion,
                "archivo_actualizado": resultado.archivo_actualizado.strftime("%Y-%m-%d %H:%M") if resultado.archivo_actualizado else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_digitalizaciones.route("/dgt_digitalizaciones")
def list_active():
    """Listado de DGT Digitalizaciones activas"""
    return render_template(
        "dgt_digitalizaciones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Digitalizaciones",
        estatus="A",
    )


@dgt_digitalizaciones.route("/dgt_digitalizaciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Digitalizaciones inactivas"""
    return render_template(
        "dgt_digitalizaciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Digitalizaciones inactivas",
        estatus="B",
    )


@dgt_digitalizaciones.route("/dgt_digitalizaciones/<dgt_digitalizacion_id>")
def detail(dgt_digitalizacion_id):
    """Detalle de una DGT Digitalización"""
    dgt_digitalizacion_id = safe_uuid(dgt_digitalizacion_id)
    if dgt_digitalizacion_id == "":
        flash("ID de DGT Digitalización inválido", "warning")
        return redirect(url_for("dgt_digitalizaciones.list_active"))
    dgt_digitalizacion = DgtDigitalizacion.query.get_or_404(dgt_digitalizacion_id)
    return render_template("dgt_digitalizaciones/detail.jinja2", dgt_digitalizacion=dgt_digitalizacion)
