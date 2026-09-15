"""
DGT Rutas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from pjecz_hercules_beta_flask.blueprints.dgt_depositos.models import DgtDepositos
from pjecz_hercules_beta_flask.blueprints.dgt_rutas.models import DgtRuta
from pjecz_hercules_beta_flask.blueprints.dgt_tipos.models import DgtTipo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_uuid

MODULO = "DGT RUTAS"

dgt_rutas = Blueprint("dgt_rutas", __name__, template_folder="templates")


@dgt_rutas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_rutas.route("/dgt_rutas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Rutas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtRuta.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(DgtRuta.clave.contains(clave))
        except ValueError:
            pass
    # Luego filtrar por columnas de otras tablas
    if "dgt_deposito_clave" in request.form:
        try:
            dgt_deposito_clave = safe_clave(request.form["dgt_deposito_clave"])
            if dgt_deposito_clave != "":
                consulta = consulta.join(DgtDepositos).filter(DgtDepositos.clave.contains(dgt_deposito_clave))
        except ValueError:
            pass
    if "dgt_tipo_clave" in request.form:
        try:
            dgt_tipo_clave = safe_clave(request.form["dgt_tipo_clave"])
            if dgt_tipo_clave != "":
                consulta = consulta.join(DgtTipo).filter(DgtTipo.clave.contains(dgt_tipo_clave))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(DgtRuta.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("dgt_rutas.detail", dgt_ruta_id=resultado.id),
                },
                "dgt_deposito_clave": resultado.dgt_deposito.clave,
                "dgt_tipo_clave": resultado.dgt_tipo.clave,
                "directorio": resultado.directorio,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_rutas.route("/dgt_rutas")
def list_active():
    """Listado de DGT Rutas activas"""
    return render_template(
        "dgt_rutas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Rutas",
        estatus="A",
    )


@dgt_rutas.route("/dgt_rutas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Rutas inactivas"""
    return render_template(
        "dgt_rutas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Rutas inactivas",
        estatus="B",
    )


@dgt_rutas.route("/dgt_rutas/<dgt_ruta_id>")
def detail(dgt_ruta_id):
    """Detalle de una DGT Ruta"""
    dgt_ruta_id = safe_uuid(dgt_ruta_id)
    if dgt_ruta_id == "":
        flash("ID de DGT Ruta inválido", "warning")
        return redirect(url_for("dgt_rutas.list_active"))
    dgt_ruta = DgtRuta.query.get_or_404(dgt_ruta_id)
    return render_template("dgt_rutas/detail.jinja2", dgt_ruta=dgt_ruta)
