"""
Listas de Acuerdos, vistas
"""

import json
import re
from datetime import datetime, time, timedelta

import pytz
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.listas_de_acuerdos.models import ListaDeAcuerdo
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

HORAS_BUENO = 14  # Bandera verde si se creó antes de 14 horas del día
HORAS_CRITICO = 16  # Bandera roja si se creó después de 16 horas del día
MODULO = "LISTAS DE ACUERDOS"

listas_de_acuerdos = Blueprint("listas_de_acuerdos", __name__, template_folder="templates")


@listas_de_acuerdos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@listas_de_acuerdos.route("/listas_de_acuerdos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Listas de Acuerdos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ListaDeAcuerdo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == "A")
    if "estatus" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(ListaDeAcuerdo.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    # Filtrar por fechas, si vienen invertidas se corrigen
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(ListaDeAcuerdo.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(ListaDeAcuerdo.fecha <= fecha_hasta)
    # Ordenar y paginar
    registros = consulta.order_by(ListaDeAcuerdo.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Tiempo
    local_tz = pytz.timezone(current_app.config["TZ"])
    medianoche = time.min
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        # La columna creado esta en UTC, convertir a local
        creado_local = resultado.creado.astimezone(local_tz)
        # Determinar el tiempo bueno
        tiempo_limite_bueno = datetime.combine(resultado.fecha, medianoche) + timedelta(hours=HORAS_BUENO)
        # Determinar el tiempo critico
        tiempo_limite_critico = datetime.combine(resultado.fecha, medianoche) + timedelta(hours=HORAS_CRITICO)
        # Por defecto el semáforo es verde (0)
        semaforo = 0
        # Si creado_local es mayor a tiempo_limite_bueno, entonces el semáforo es amarillo (1)
        if creado_local > local_tz.localize(tiempo_limite_bueno):
            semaforo = 1
        # Si creado_local es mayor a tiempo_limite_critico, entonces el semáforo es rojo (2)
        if creado_local > local_tz.localize(tiempo_limite_critico):
            semaforo = 2
        # Acumular fila
        data.append(
            {
                "detalle": {
                    "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                    "url": url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=resultado.id),
                },
                "autoridad_clave": resultado.autoridad.clave,
                "descripcion": resultado.descripcion,
                "descargar_url": resultado.descargar_url,
                "creado": {
                    "tiempo": creado_local.strftime("%Y-%m-%dT%H:%M:%S"),
                    "semaforo": semaforo,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@listas_de_acuerdos.route("/listas_de_acuerdos")
def list_active():
    """Listado de Listas de Acuerdos activos"""
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


@listas_de_acuerdos.route("/listas_de_acuerdos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Listas de Acuerdos inactivos"""
    return render_template(
        "listas_de_acuerdos/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Listas de Acuerdos inactivos",
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/<int:lista_de_acuerdo_id>")
def detail(lista_de_acuerdo_id):
    """Detalle de un Lista de Acuerdo"""
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)
    return render_template("listas_de_acuerdos/detail.jinja2", lista_de_acuerdo=lista_de_acuerdo)
