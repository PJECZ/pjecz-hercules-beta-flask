"""
DGT Tipos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from pjecz_hercules_beta_flask.blueprints.dgt_tipos.models import DgtTipo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_string, safe_uuid

MODULO = "DGT TIPOS"

dgt_tipos = Blueprint("dgt_tipos", __name__, template_folder="templates")


@dgt_tipos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_tipos.route("/dgt_tipos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Tipos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtTipo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(DgtTipo.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(DgtTipo.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(DgtTipo.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("dgt_tipos.detail", dgt_tipo_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_tipos.route("/dgt_tipos")
def list_active():
    """Listado de DGT Tipos activos"""
    return render_template(
        "dgt_tipos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Tipos",
        estatus="A",
    )


@dgt_tipos.route("/dgt_tipos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Tipos inactivos"""
    return render_template(
        "dgt_tipos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Tipos inactivos",
        estatus="B",
    )


@dgt_tipos.route("/dgt_tipos/<dgt_tipo_id>")
def detail(dgt_tipo_id):
    """Detalle de un DGT Tipo"""
    dgt_tipo_id = safe_uuid(dgt_tipo_id)
    if dgt_tipo_id == "":
        flash("ID de DGT Tipo inválido", "warning")
        return redirect(url_for("dgt_tipos.list_active"))
    dgt_tipo = DgtTipo.query.get_or_404(dgt_tipo_id)
    return render_template("dgt_tipos/detail.jinja2", dgt_tipo=dgt_tipo)
