"""
App Aplicaciones, vistas
"""

import json
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.app_aplicaciones.forms import AppAplicacionForm
from pjecz_hercules_beta_flask.blueprints.app_aplicaciones.models import AppAplicacion
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.pwgen import generar_api_key_aplicacion
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "APP APLICACIONES"
API_KEY_DIAS_POR_DEFECTO = 90
API_KEY_DIAS_MAXIMO = 3650

app_aplicaciones = Blueprint("app_aplicaciones", __name__, template_folder="templates")


@app_aplicaciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@app_aplicaciones.route("/app_aplicaciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de App Aplicaciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = AppAplicacion.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(AppAplicacion.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(AppAplicacion.estatus == "A")
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"], max_len=16)
        if clave != "":
            consulta = consulta.filter(AppAplicacion.clave.contains(clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(AppAplicacion.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(AppAplicacion.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "clave": item.clave,
                    "url": url_for("app_aplicaciones.detail", app_aplicacion_id=item.id),
                },
                "descripcion": item.descripcion,
                "cuota_diaria": item.cuota_diaria,
                "cuota_por_hora": item.cuota_por_hora,
                "api_key_oculta": item.api_key_oculta,
                "expiracion": item.expiracion.strftime("%Y-%m-%d %H:%M") if item.expiracion else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@app_aplicaciones.route("/app_aplicaciones")
def list_active():
    """Listado de App Aplicaciones activas"""
    return render_template(
        "app_aplicaciones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Aplicaciones",
        estatus="A",
    )


@app_aplicaciones.route("/app_aplicaciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de App Aplicaciones inactivas"""
    return render_template(
        "app_aplicaciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Aplicaciones inactivas",
        estatus="B",
    )


@app_aplicaciones.route("/app_aplicaciones/<app_aplicacion_id>")
def detail(app_aplicacion_id):
    """Detalle de una App Aplicación"""
    app_aplicacion_id = safe_uuid(app_aplicacion_id)
    if app_aplicacion_id == "":
        flash("ID de aplicación inválido", "warning")
        return redirect(url_for("app_aplicaciones.list_active"))
    app_aplicacion = AppAplicacion.query.get_or_404(app_aplicacion_id)
    return render_template("app_aplicaciones/detail.jinja2", app_aplicacion=app_aplicacion)


@app_aplicaciones.route("/app_aplicaciones/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva App Aplicación"""
    form = AppAplicacionForm()
    if form.validate_on_submit():
        clave = safe_clave(form.clave.data, max_len=16)
        descripcion = safe_string(form.descripcion.data, max_len=256, save_enie=True)
        # Validar que la clave sea válida
        if clave == "":
            flash("La clave es inválida.", "warning")
            return render_template("app_aplicaciones/new.jinja2", form=form)
        # Validar que la clave no se repita
        if AppAplicacion.query.filter_by(clave=clave).first():
            flash("Esa clave ya está en uso. Debe de ser única.", "warning")
            return render_template("app_aplicaciones/new.jinja2", form=form)
        # Guardar
        app_aplicacion = AppAplicacion(
            clave=clave,
            descripcion=descripcion,
            cuota_diaria=form.cuota_diaria.data,
            cuota_por_hora=form.cuota_por_hora.data,
        )
        app_aplicacion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva aplicación {app_aplicacion.clave}"),
            url=url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("app_aplicaciones/new.jinja2", form=form)


@app_aplicaciones.route("/app_aplicaciones/edicion/<app_aplicacion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(app_aplicacion_id):
    """Editar App Aplicación"""
    app_aplicacion_id = safe_uuid(app_aplicacion_id)
    if app_aplicacion_id == "":
        flash("ID de aplicación inválido", "warning")
        return redirect(url_for("app_aplicaciones.list_active"))
    app_aplicacion = AppAplicacion.query.get_or_404(app_aplicacion_id)
    form = AppAplicacionForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar la clave y, si cambia, verificar que no esté en uso
        clave = safe_clave(form.clave.data, max_len=16)
        if clave == "":
            es_valido = False
            flash("La clave es inválida.", "warning")
        elif app_aplicacion.clave != clave:
            app_aplicacion_existente = AppAplicacion.query.filter_by(clave=clave).first()
            if app_aplicacion_existente and app_aplicacion_existente.id != app_aplicacion.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es válido actualizar
        if es_valido:
            app_aplicacion.clave = clave
            app_aplicacion.descripcion = safe_string(form.descripcion.data, max_len=256, save_enie=True)
            app_aplicacion.cuota_diaria = form.cuota_diaria.data
            app_aplicacion.cuota_por_hora = form.cuota_por_hora.data
            app_aplicacion.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada aplicación {app_aplicacion.clave}"),
                url=url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    if request.method == "GET":
        form.clave.data = app_aplicacion.clave
        form.descripcion.data = app_aplicacion.descripcion
        form.cuota_diaria.data = app_aplicacion.cuota_diaria
        form.cuota_por_hora.data = app_aplicacion.cuota_por_hora
    return render_template("app_aplicaciones/edit.jinja2", form=form, app_aplicacion=app_aplicacion)


@app_aplicaciones.route("/app_aplicaciones/eliminar/<app_aplicacion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(app_aplicacion_id):
    """Eliminar App Aplicación"""
    app_aplicacion_id = safe_uuid(app_aplicacion_id)
    if app_aplicacion_id == "":
        flash("ID de aplicación inválido", "warning")
        return redirect(url_for("app_aplicaciones.list_active"))
    app_aplicacion = AppAplicacion.query.get_or_404(app_aplicacion_id)
    if app_aplicacion.estatus == "A":
        app_aplicacion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada aplicación {app_aplicacion.clave}"),
            url=url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id))


@app_aplicaciones.route("/app_aplicaciones/recuperar/<app_aplicacion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(app_aplicacion_id):
    """Recuperar App Aplicación"""
    app_aplicacion_id = safe_uuid(app_aplicacion_id)
    if app_aplicacion_id == "":
        flash("ID de aplicación inválido", "warning")
        return redirect(url_for("app_aplicaciones.list_active"))
    app_aplicacion = AppAplicacion.query.get_or_404(app_aplicacion_id)
    if app_aplicacion.estatus == "B":
        app_aplicacion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada aplicación {app_aplicacion.clave}"),
            url=url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id))


@app_aplicaciones.route("/app_aplicaciones/api_key_request_json/<app_aplicacion_id>", methods=["POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def api_key_request_json(app_aplicacion_id):
    """Generar o limpiar la API key de una App Aplicación"""
    app_aplicacion_id = safe_uuid(app_aplicacion_id)
    if app_aplicacion_id == "":
        return {"success": False, "message": "ID de aplicación inválido", "api_key": "", "expiracion": ""}
    app_aplicacion = AppAplicacion.query.get_or_404(app_aplicacion_id)
    if app_aplicacion.estatus != "A":
        return {"success": False, "message": "La aplicación no está activa", "api_key": "", "expiracion": ""}
    action = request.form.get("action", "")

    # Si se recibe action con clean, se va a limpiar
    if action == "clean":
        app_aplicacion.api_key = ""
        app_aplicacion.expiracion = datetime(year=2000, month=1, day=1)
        app_aplicacion.save()
        mensaje = f"La API key de la aplicación {app_aplicacion.clave} fue eliminada"
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(mensaje),
            url=url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id),
        )
        bitacora.save()
        return {
            "success": True,
            "message": mensaje,
            "api_key": "",
            "expiracion": app_aplicacion.expiracion.strftime("%Y-%m-%d %H:%M"),
        }

    # Si se recibe action con new, se va a crear una nueva
    if action == "new":
        try:
            days = int(request.form.get("days") or API_KEY_DIAS_POR_DEFECTO)
        except ValueError:
            return {"success": False, "message": "Los días deben ser un número entero", "api_key": "", "expiracion": ""}
        if days < 1 or days > API_KEY_DIAS_MAXIMO:
            return {
                "success": False,
                "message": f"Los días deben estar entre 1 y {API_KEY_DIAS_MAXIMO}",
                "api_key": "",
                "expiracion": "",
            }
        app_aplicacion.api_key = generar_api_key_aplicacion(app_aplicacion.clave)
        app_aplicacion.expiracion = datetime.now() + timedelta(days=days)
        app_aplicacion.save()
        mensaje = f"Nueva API key para la aplicación {app_aplicacion.clave} con expiración en {days} días"
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(mensaje),
            url=url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id),
        )
        bitacora.save()
        return {
            "success": True,
            "message": mensaje,
            "api_key": app_aplicacion.api_key,
            "expiracion": app_aplicacion.expiracion.strftime("%Y-%m-%d %H:%M"),
        }

    # Cualquier otra acción no es válida
    return {"success": False, "message": "Acción no válida", "api_key": "", "expiracion": ""}
