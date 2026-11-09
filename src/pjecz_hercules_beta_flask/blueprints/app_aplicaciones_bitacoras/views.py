"""
App Aplicaciones Bitácoras, vistas (solo consulta)
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.app_aplicaciones.models import AppAplicacion
from pjecz_hercules_beta_flask.blueprints.app_aplicaciones_bitacoras.models import AppAplicacionBitacora
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_uuid

MODULO = "APP APLICACIONES BITACORAS"

app_aplicaciones_bitacoras = Blueprint("app_aplicaciones_bitacoras", __name__, template_folder="templates")


@app_aplicaciones_bitacoras.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@app_aplicaciones_bitacoras.route("/app_aplicaciones_bitacoras/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de App Aplicaciones Bitácoras"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = AppAplicacionBitacora.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(AppAplicacionBitacora.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(AppAplicacionBitacora.estatus == "A")
    if "app_aplicacion_id" in request.form:
        app_aplicacion_id = safe_uuid(request.form["app_aplicacion_id"])
        if app_aplicacion_id != "":
            consulta = consulta.filter(AppAplicacionBitacora.app_aplicacion_id == app_aplicacion_id)
    if "peticion" in request.form:
        peticion = request.form["peticion"].strip().upper()
        if peticion in AppAplicacionBitacora.PETICIONES:
            consulta = consulta.filter(AppAplicacionBitacora.peticion == peticion)
    if "respuesta_estado" in request.form:
        try:
            consulta = consulta.filter(AppAplicacionBitacora.respuesta_estado == int(request.form["respuesta_estado"]))
        except ValueError:
            pass
    # Luego filtrar por columnas de otras tablas
    if "app_aplicacion_clave" in request.form:
        app_aplicacion_clave = safe_clave(request.form["app_aplicacion_clave"], max_len=16)
        if app_aplicacion_clave != "":
            consulta = consulta.join(AppAplicacion).filter(AppAplicacion.clave.contains(app_aplicacion_clave))
    # Ordenar y paginar
    registros = consulta.order_by(AppAplicacionBitacora.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "creado": item.creado.strftime("%Y-%m-%d %H:%M:%S") if item.creado else "",
                    "url": url_for("app_aplicaciones_bitacoras.detail", app_aplicacion_bitacora_id=item.id),
                },
                "app_aplicacion": {
                    "clave": item.app_aplicacion.clave,
                    "url": (
                        url_for("app_aplicaciones.detail", app_aplicacion_id=item.app_aplicacion_id)
                        if current_user.can_view("APP APLICACIONES")
                        else ""
                    ),
                },
                "peticion": item.peticion,
                "ruta": item.ruta,
                "respuesta_estado": item.respuesta_estado,
                "es_exitosa": item.es_exitosa,
                "respuesta_mensaje": item.respuesta_mensaje,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@app_aplicaciones_bitacoras.route("/app_aplicaciones_bitacoras")
def list_active():
    """Listado de App Aplicaciones Bitácoras"""
    return render_template(
        "app_aplicaciones_bitacoras/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Bitácoras de aplicaciones",
        estatus="A",
        peticiones=AppAplicacionBitacora.PETICIONES,
    )


@app_aplicaciones_bitacoras.route("/app_aplicaciones_bitacoras/<app_aplicacion_bitacora_id>")
def detail(app_aplicacion_bitacora_id):
    """Detalle de una App Aplicación Bitácora"""
    app_aplicacion_bitacora_id = safe_uuid(app_aplicacion_bitacora_id)
    if app_aplicacion_bitacora_id == "":
        flash("ID de bitácora de aplicación inválido", "warning")
        return redirect(url_for("app_aplicaciones_bitacoras.list_active"))
    app_aplicacion_bitacora = AppAplicacionBitacora.query.get_or_404(app_aplicacion_bitacora_id)
    return render_template(
        "app_aplicaciones_bitacoras/detail.jinja2",
        app_aplicacion_bitacora=app_aplicacion_bitacora,
        creado=app_aplicacion_bitacora.creado.strftime("%Y-%m-%d %H:%M:%S") if app_aplicacion_bitacora.creado else "",
    )
