"""
Bitácoras de APIs
"""

import json
from datetime import date, timedelta

from flask import Blueprint, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras_apis.models import BitacoraAPI
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.blueprints.usuarios.models import Usuario
from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json

MODULO = "BITACORAS APIS"

bitacoras_apis = Blueprint("bitacoras_apis", __name__, template_folder="templates")


@bitacoras_apis.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@bitacoras_apis.route("/bitacoras_apis/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Bitacoras APIs"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = BitacoraAPI.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(BitacoraAPI.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(BitacoraAPI.estatus == "A")
    if "usuario_id" in request.form:
        try:
            usuario_id = int(request.form["usuario_id"])
            consulta = consulta.filter(BitacoraAPI.usuario_id == usuario_id)
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(BitacoraAPI.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "usuario": {
                    "email": resultado.usuario.email,
                    "url": (
                        url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else ""
                    ),
                },
                "api_nombre": resultado.api_nombre,
                "api_ruta": resultado.api_ruta,
                "peticion": resultado.peticion,
                "respuesta_mensaje": resultado.respuesta_mensaje if resultado.respuesta_mensaje else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@bitacoras_apis.route("/bitacoras_apis")
def list_active():
    """Listado de Bitácoras APIs activas"""
    # Valores por defecto
    filtros = {"estatus": "A"}
    titulo = "Bitácoras APIs"
    # Si viene usuario_id en la URL, agregar a los filtros
    filtros = {"estatus": "A"}
    usuario_id = request.args.get("usuario_id")
    titulo = "Bitácoras de APIs"
    if usuario_id:
        filtros["usuario_id"] = usuario_id
        usuario = Usuario.query.get_or_404(usuario_id)
        titulo = f"Bitácoras de APIs de {usuario.nombre}"
    # Entregar
    return render_template(
        "bitacoras_apis/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
    )


@bitacoras_apis.route("/bitacoras_apis/obtener_totales_por_usuario")
def get_totales_por_usuario_json():
    """Obtener los totales de Bitácoras APIs por usuario en JSON"""

    # Validar las fechas inicial y final, en formato AAAA-MM-DD
    try:
        fecha_inicial = date.fromisoformat(request.args["fecha_inicial"])
        fecha_final = date.fromisoformat(request.args["fecha_final"])
    except (KeyError, ValueError):
        return {
            "success": False,
            "message": "Las fechas inicial y final son requeridas en formato AAAA-MM-DD",
            "totales": [],
        }
    if fecha_inicial > fecha_final:
        return {
            "success": False,
            "message": "La fecha inicial no puede ser posterior a la fecha final",
            "totales": [],
        }

    # Consultar los totales por usuario, incluyendo todo el día de la fecha final
    total = func.count(BitacoraAPI.id).label("total")
    consulta = (
        database.session.query(
            Usuario.id.label("usuario_id"),
            Usuario.email.label("usuario_email"),
            Usuario.api_key_cuota_diaria.label("api_key_cuota_diaria"),
            Usuario.api_key_expiracion.label("api_key_expiracion"),
            Autoridad.clave.label("autoridad_clave"),
            total,
        )
        .select_from(
            BitacoraAPI,
        )
        .join(
            Usuario,
            BitacoraAPI.usuario_id == Usuario.id,
        )
        .join(
            Autoridad,
            Usuario.autoridad_id == Autoridad.id,
        )
        .where(
            BitacoraAPI.estatus == "A",
            BitacoraAPI.creado >= fecha_inicial,
            BitacoraAPI.creado < fecha_final + timedelta(days=1),
        )
        .group_by(
            Usuario.id,
            Usuario.email,
            Usuario.api_key_cuota_diaria,
            Usuario.api_key_expiracion,
            Autoridad.clave,
        )
        .order_by(
            total.desc(),
            Usuario.email,
        )
        .all()
    )

    # Entregar la lista de totales
    return {
        "success": True,
        "message": "Entrega exitosa del listado de totales por usuario",
        "totales": [
            {
                "usuario_id": row.usuario_id,
                "usuario_email": row.usuario_email,
                "autoridad_clave": row.autoridad_clave,
                "api_key_cuota_diaria": row.api_key_cuota_diaria,
                "api_key_expiracion": row.api_key_expiracion.strftime("%Y-%m-%d") if row.api_key_expiracion else None,
                "total": row.total,
            }
            for row in consulta
        ],
    }


@bitacoras_apis.route("/bitacoras_apis/dashboard_por_usuario")
def dashboard_por_usuario():
    """Tablero de Bitácoras APIs por usuario"""
    return render_template("bitacoras_apis/dashboard_por_usuario.jinja2")
