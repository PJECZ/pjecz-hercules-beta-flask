"""
DGT Entregas, vistas
"""

import json
from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import Date, cast, func

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.dgt_entregas.models import DgtEntrega
from pjecz_hercules_beta_flask.blueprints.materias.models import Materia
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_string, safe_uuid

MODULO = "DGT ENTREGAS"

dgt_entregas = Blueprint("dgt_entregas", __name__, template_folder="templates")


@dgt_entregas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_entregas.route("/dgt_entregas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Entregas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtEntrega.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "expediente" in request.form:
        expediente = safe_string(request.form["expediente"])
        if expediente != "":
            consulta = consulta.filter(DgtEntrega.expediente.contains(expediente))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(DgtEntrega.descripcion.contains(descripcion))
    if "dgt_ruta_id" in request.form:
        consulta = consulta.filter(DgtEntrega.dgt_ruta_id == request.form["dgt_ruta_id"])
    if "expediente_anio" in request.form:
        try:
            expediente_anio = int(request.form["expediente_anio"])
            consulta = consulta.filter(DgtEntrega.expediente_anio == expediente_anio)
        except ValueError:
            pass
    # Luego filtrar por columnas de otras tablas
    autoridad_unida = False
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
                autoridad_unida = True
        except ValueError:
            pass
    if "materia_id" in request.form:
        try:
            materia_id = int(request.form["materia_id"])
            if not autoridad_unida:
                consulta = consulta.join(Autoridad)
            consulta = consulta.filter(Autoridad.materia_id == materia_id)
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(DgtEntrega.archivo_actualizado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "archivo_nombre": resultado.archivo_nombre,
                    "url": url_for("dgt_entregas.detail", dgt_entrega_id=resultado.id),
                },
                "autoridad_clave": resultado.autoridad.clave,
                "expediente": resultado.expediente,
                "descripcion": resultado.descripcion,
                "dgt_tipo_clave": resultado.dgt_ruta.dgt_tipo.clave,
                "archivo_actualizado": resultado.archivo_actualizado.strftime("%Y-%m-%d %H:%M"),
                "ultimo_evento": {
                    "evento": resultado.ultimo_evento,
                    "creado": resultado.ultimo_evento_creado.strftime("%Y-%m-%d %H:%M") if resultado.ultimo_evento_creado else "",
                },
                "archivo_uuid": resultado.archivo_uuid,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_entregas.route("/dgt_entregas")
def list_active():
    """Listado de DGT Entregas activas"""
    filtros = {"estatus": "A"}
    titulo = "DGT Entregas"
    # Si viene el año del expediente, filtrar por éste
    if "expediente_anio" in request.args:
        try:
            expediente_anio = int(request.args["expediente_anio"])
            filtros["expediente_anio"] = expediente_anio
            titulo = f"{titulo} del año {expediente_anio}"
        except (KeyError, ValueError):
            pass
    # Si viene la materia, filtrar por ésta
    if "materia_id" in request.args:
        try:
            materia = Materia.query.get(int(request.args["materia_id"]))
            if materia is not None:
                filtros["materia_id"] = materia.id
                titulo = f"{titulo} en {materia.nombre}"
        except (KeyError, ValueError):
            pass
    return render_template(
        "dgt_entregas/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
        estatus="A",
    )


@dgt_entregas.route("/dgt_entregas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Entregas inactivas"""
    return render_template(
        "dgt_entregas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Entregas inactivas",
        estatus="B",
    )


@dgt_entregas.route("/dgt_entregas/<dgt_entrega_id>")
def detail(dgt_entrega_id):
    """Detalle de una DGT Entrega"""
    dgt_entrega_id = safe_uuid(dgt_entrega_id)
    if dgt_entrega_id == "":
        flash("ID de DGT Entrega inválido", "warning")
        return redirect(url_for("dgt_entregas.list_active"))
    dgt_entrega = DgtEntrega.query.get_or_404(dgt_entrega_id)
    return render_template("dgt_entregas/detail.jinja2", dgt_entrega=dgt_entrega)


@dgt_entregas.route("/dgt_entregas/obtener_totales_por_expediente_anio")
def get_totales_por_expediente_anio_json():
    """Obtener los totales de DGT Entregas por materia y por año en JSON"""

    # Consultar los totales (copiados, enviados) por materia por año
    consulta = (
        database.session.query(
            Materia.id.label("materia_id"),
            Materia.nombre.label("materia"),
            DgtEntrega.expediente_anio.label("anio"),
            func.count(DgtEntrega.id).label("total"),
        )
        .select_from(
            DgtEntrega,
        )
        .join(
            Autoridad,
        )
        .join(
            Materia,
        )
        .where(
            DgtEntrega.estatus == "A",
        )
        .group_by(
            Materia.id,
            Materia.nombre,
            DgtEntrega.expediente_anio,
        )
        .order_by(
            DgtEntrega.expediente_anio,
            Materia.nombre,
        )
        .all()
    )

    # Entregar la lista de totales
    return {
        "success": True,
        "message": "Entrega exitosa del listado de totales por materia",
        "totales": [
            {
                "materia_id": row.materia_id,
                "materia_nombre": row.materia,
                "anio": row.anio,
                "total": row.total,
            }
            for row in consulta
        ],
    }


@dgt_entregas.route("/dgt_entregas/obtener_totales_por_materia_por_archivo_actualizado")
def get_totales_por_materia_por_archivo_actualizado_json():
    """Obtener los totales de DGT Entregas por materia y por fecha de archivo actualizado en JSON"""

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

    # Tomar solo la fecha de archivo_actualizado para agrupar
    fecha = cast(DgtEntrega.archivo_actualizado, Date)

    # Consultar los totales por materia por fecha, incluyendo todo el día de la fecha final
    consulta = (
        database.session.query(
            Materia.id.label("materia_id"),
            Materia.nombre.label("materia"),
            fecha.label("fecha"),
            func.count(DgtEntrega.id).label("total"),
        )
        .select_from(
            DgtEntrega,
        )
        .join(
            Autoridad,
        )
        .join(
            Materia,
        )
        .where(
            DgtEntrega.estatus == "A",
            DgtEntrega.archivo_actualizado >= fecha_inicial,
            DgtEntrega.archivo_actualizado < fecha_final + timedelta(days=1),
        )
        .group_by(
            Materia.id,
            Materia.nombre,
            fecha,
        )
        .order_by(
            fecha,
            Materia.nombre,
        )
        .all()
    )

    # Entregar la lista de totales
    return {
        "success": True,
        "message": "Entrega exitosa del listado de totales por materia y por fecha de archivo actualizado",
        "totales": [
            {
                "materia_id": row.materia_id,
                "materia_nombre": row.materia,
                "fecha": row.fecha.isoformat(),
                "total": row.total,
            }
            for row in consulta
        ],
    }


@dgt_entregas.route("/dgt_entregas/dashboard_por_expediente_anio")
def dashboard_por_expediente_anio():
    """Tablero de DGT Entregas por año del expediente"""
    return render_template("dgt_entregas/dashboard_por_expediente_anio.jinja2")
