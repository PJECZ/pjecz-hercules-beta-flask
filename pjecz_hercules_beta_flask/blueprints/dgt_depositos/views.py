"""
DGT Depósitos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from pjecz_hercules_beta_flask.blueprints.dgt_depositos.models import DgtDepositos
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_string, safe_uuid

MODULO = "DGT DEPOSITOS"

dgt_depositos = Blueprint("dgt_depositos", __name__, template_folder="templates")


@dgt_depositos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_depositos.route("/dgt_depositos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Depósitos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtDepositos.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(DgtDepositos.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(DgtDepositos.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(DgtDepositos.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("dgt_depositos.detail", dgt_deposito_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_depositos.route("/dgt_depositos")
def list_active():
    """Listado de DGT Depósitos activos"""
    return render_template(
        "dgt_depositos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Depósitos",
        estatus="A",
    )


@dgt_depositos.route("/dgt_depositos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Depósitos inactivos"""
    return render_template(
        "dgt_depositos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Depósitos inactivos",
        estatus="B",
    )


@dgt_depositos.route("/dgt_depositos/<dgt_deposito_id>")
def detail(dgt_deposito_id):
    """Detalle de un DGT Depósito"""
    dgt_deposito_id = safe_uuid(dgt_deposito_id)
    if dgt_deposito_id == "":
        flash("ID de DGT Depósito inválido", "warning")
        return redirect(url_for("dgt_depositos.list_active"))
    dgt_deposito = DgtDepositos.query.get_or_404(dgt_deposito_id)
    return render_template("dgt_depositos/detail.jinja2", dgt_deposito=dgt_deposito)
