"""
App Aplicaciones Roles, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.app_aplicaciones.models import AppAplicacion
from pjecz_hercules_beta_flask.blueprints.app_aplicaciones_roles.forms import (
    AppAplicacionRolEditForm,
    AppAplicacionRolWithAppAplicacionForm,
)
from pjecz_hercules_beta_flask.blueprints.app_aplicaciones_roles.models import AppAplicacionRol
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.roles.models import Rol
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "APP APLICACIONES ROLES"

app_aplicaciones_roles = Blueprint("app_aplicaciones_roles", __name__, template_folder="templates")


@app_aplicaciones_roles.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@app_aplicaciones_roles.route("/app_aplicaciones_roles/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de App Aplicaciones Roles"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = AppAplicacionRol.query.join(AppAplicacion).join(Rol)
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        if request.form["estatus"] in ("A", "B"):
            consulta = consulta.filter(AppAplicacionRol.estatus == request.form["estatus"])
        # Cualquier otro valor (por ejemplo "todos") no filtra por estatus
    else:
        consulta = consulta.filter(AppAplicacionRol.estatus == "A")
    if "app_aplicacion_id" in request.form:
        app_aplicacion_id = safe_uuid(request.form["app_aplicacion_id"])
        if app_aplicacion_id != "":
            consulta = consulta.filter(AppAplicacionRol.app_aplicacion_id == app_aplicacion_id)
    if "rol_id" in request.form:
        try:
            consulta = consulta.filter(AppAplicacionRol.rol_id == int(request.form["rol_id"]))
        except ValueError:
            pass
    if "nivel" in request.form:
        try:
            consulta = consulta.filter(AppAplicacionRol.nivel == int(request.form["nivel"]))
        except ValueError:
            pass
    # Luego filtrar por columnas de otras tablas
    if "app_aplicacion_clave" in request.form:
        app_aplicacion_clave = safe_clave(request.form["app_aplicacion_clave"], max_len=16)
        if app_aplicacion_clave != "":
            consulta = consulta.filter(AppAplicacion.clave.contains(app_aplicacion_clave))
    if "rol_nombre" in request.form:
        rol_nombre = safe_string(request.form["rol_nombre"], save_enie=True)
        if rol_nombre != "":
            consulta = consulta.filter(Rol.nombre.contains(rol_nombre))
    # Ordenar y paginar
    registros = consulta.order_by(AppAplicacion.clave, Rol.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": str(resultado.id),
                    "url": url_for("app_aplicaciones_roles.detail", app_aplicacion_rol_id=resultado.id),
                },
                "app_aplicacion": {
                    "clave": resultado.app_aplicacion.clave,
                    "url": (
                        url_for("app_aplicaciones.detail", app_aplicacion_id=resultado.app_aplicacion_id)
                        if current_user.can_view("APP APLICACIONES")
                        else ""
                    ),
                },
                "rol": {
                    "nombre": resultado.rol.nombre,
                    "url": url_for("roles.detail", rol_id=resultado.rol_id) if current_user.can_view("ROLES") else "",
                },
                "nivel": resultado.nivel,
                "nivel_descrito": resultado.nivel_descrito,
                "estatus": resultado.estatus,
                "toggle_estatus": {
                    "id": str(resultado.id),
                    "estatus": resultado.estatus,
                    "url": (
                        url_for("app_aplicaciones_roles.toggle_estatus_json", app_aplicacion_rol_id=resultado.id)
                        if current_user.can_admin(MODULO)
                        else ""
                    ),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@app_aplicaciones_roles.route("/app_aplicaciones_roles")
def list_active():
    """Listado de App Aplicaciones Roles activos"""
    return render_template(
        "app_aplicaciones_roles/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Aplicaciones-Roles",
        estatus="A",
    )


@app_aplicaciones_roles.route("/app_aplicaciones_roles/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de App Aplicaciones Roles inactivos"""
    return render_template(
        "app_aplicaciones_roles/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Aplicaciones-Roles inactivos",
        estatus="B",
    )


@app_aplicaciones_roles.route("/app_aplicaciones_roles/<app_aplicacion_rol_id>")
def detail(app_aplicacion_rol_id):
    """Detalle de un App Aplicación Rol"""
    app_aplicacion_rol_id = safe_uuid(app_aplicacion_rol_id)
    if app_aplicacion_rol_id == "":
        flash("ID de aplicación-rol inválido", "warning")
        return redirect(url_for("app_aplicaciones_roles.list_active"))
    app_aplicacion_rol = AppAplicacionRol.query.get_or_404(app_aplicacion_rol_id)
    return render_template("app_aplicaciones_roles/detail.jinja2", app_aplicacion_rol=app_aplicacion_rol)


@app_aplicaciones_roles.route("/app_aplicaciones_roles/nuevo_con_app_aplicacion/<app_aplicacion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_app_aplicacion(app_aplicacion_id):
    """Agregar un rol a una App Aplicación; si la pareja ya existe, actualiza el nivel y la reactiva"""
    app_aplicacion_id = safe_uuid(app_aplicacion_id)
    if app_aplicacion_id == "":
        flash("ID de aplicación inválido", "warning")
        return redirect(url_for("app_aplicaciones.list_active"))
    app_aplicacion = AppAplicacion.query.get_or_404(app_aplicacion_id)
    if app_aplicacion.estatus != "A":
        flash("La aplicación no está activa.", "warning")
        return redirect(url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id))
    form = AppAplicacionRolWithAppAplicacionForm()
    if form.validate_on_submit():
        rol = Rol.query.get_or_404(form.rol.data)
        nivel = form.nivel.data
        descripcion = f"{app_aplicacion.clave} puede {AppAplicacionRol.NIVELES[nivel]} con el rol {rol.nombre}"
        app_aplicacion_rol = (
            AppAplicacionRol.query.filter_by(app_aplicacion_id=app_aplicacion.id).filter_by(rol_id=rol.id).first()
        )
        if app_aplicacion_rol is not None:
            # Ya existe la pareja: actualizar el nivel y reactivar
            app_aplicacion_rol.nivel = nivel
            app_aplicacion_rol.estatus = "A"
            app_aplicacion_rol.save()
            mensaje = f"Actualizado aplicación-rol {descripcion}"
        else:
            app_aplicacion_rol = AppAplicacionRol(
                app_aplicacion=app_aplicacion,
                rol=rol,
                nivel=nivel,
            )
            app_aplicacion_rol.save()
            mensaje = f"Nuevo aplicación-rol {descripcion}"
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(mensaje),
            url=url_for("app_aplicaciones.detail", app_aplicacion_id=app_aplicacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.app_aplicacion_clave.data = app_aplicacion.clave  # Solo lectura
    return render_template(
        "app_aplicaciones_roles/new_with_app_aplicacion.jinja2",
        form=form,
        app_aplicacion=app_aplicacion,
        titulo=f"Agregar rol a la aplicación {app_aplicacion.clave}",
    )


@app_aplicaciones_roles.route("/app_aplicaciones_roles/edicion/<app_aplicacion_rol_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(app_aplicacion_rol_id):
    """Editar el nivel de un App Aplicación Rol"""
    app_aplicacion_rol_id = safe_uuid(app_aplicacion_rol_id)
    if app_aplicacion_rol_id == "":
        flash("ID de aplicación-rol inválido", "warning")
        return redirect(url_for("app_aplicaciones_roles.list_active"))
    app_aplicacion_rol = AppAplicacionRol.query.get_or_404(app_aplicacion_rol_id)
    form = AppAplicacionRolEditForm()
    if form.validate_on_submit():
        app_aplicacion_rol.nivel = form.nivel.data
        app_aplicacion_rol.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(
                f"Editado aplicación-rol {app_aplicacion_rol.app_aplicacion.clave} puede "
                f"{app_aplicacion_rol.nivel_descrito} con el rol {app_aplicacion_rol.rol.nombre}"
            ),
            url=url_for("app_aplicaciones_roles.detail", app_aplicacion_rol_id=app_aplicacion_rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.app_aplicacion_clave.data = app_aplicacion_rol.app_aplicacion.clave  # Solo lectura
    form.rol_nombre.data = app_aplicacion_rol.rol.nombre  # Solo lectura
    if request.method == "GET":
        form.nivel.data = app_aplicacion_rol.nivel
    return render_template("app_aplicaciones_roles/edit.jinja2", form=form, app_aplicacion_rol=app_aplicacion_rol)


@app_aplicaciones_roles.route("/app_aplicaciones_roles/eliminar/<app_aplicacion_rol_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(app_aplicacion_rol_id):
    """Eliminar App Aplicación Rol"""
    app_aplicacion_rol_id = safe_uuid(app_aplicacion_rol_id)
    if app_aplicacion_rol_id == "":
        flash("ID de aplicación-rol inválido", "warning")
        return redirect(url_for("app_aplicaciones_roles.list_active"))
    app_aplicacion_rol = AppAplicacionRol.query.get_or_404(app_aplicacion_rol_id)
    if app_aplicacion_rol.estatus == "A":
        app_aplicacion_rol.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(
                f"Eliminado aplicación-rol {app_aplicacion_rol.app_aplicacion.clave} con el rol {app_aplicacion_rol.rol.nombre}"
            ),
            url=url_for("app_aplicaciones_roles.detail", app_aplicacion_rol_id=app_aplicacion_rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("app_aplicaciones_roles.detail", app_aplicacion_rol_id=app_aplicacion_rol.id))


@app_aplicaciones_roles.route("/app_aplicaciones_roles/recuperar/<app_aplicacion_rol_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(app_aplicacion_rol_id):
    """Recuperar App Aplicación Rol"""
    app_aplicacion_rol_id = safe_uuid(app_aplicacion_rol_id)
    if app_aplicacion_rol_id == "":
        flash("ID de aplicación-rol inválido", "warning")
        return redirect(url_for("app_aplicaciones_roles.list_active"))
    app_aplicacion_rol = AppAplicacionRol.query.get_or_404(app_aplicacion_rol_id)
    if app_aplicacion_rol.estatus == "B":
        app_aplicacion_rol.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(
                f"Recuperado aplicación-rol {app_aplicacion_rol.app_aplicacion.clave} con el rol {app_aplicacion_rol.rol.nombre}"
            ),
            url=url_for("app_aplicaciones_roles.detail", app_aplicacion_rol_id=app_aplicacion_rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("app_aplicaciones_roles.detail", app_aplicacion_rol_id=app_aplicacion_rol.id))


@app_aplicaciones_roles.route("/app_aplicaciones_roles/toggle_estatus_json/<app_aplicacion_rol_id>", methods=["POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def toggle_estatus_json(app_aplicacion_rol_id):
    """Cambiar el estatus de un App Aplicación Rol por solicitud del botón en el datatable"""
    app_aplicacion_rol_id = safe_uuid(app_aplicacion_rol_id)
    if app_aplicacion_rol_id == "":
        return {"success": False, "message": "ID de aplicación-rol inválido"}
    app_aplicacion_rol = AppAplicacionRol.query.get_or_404(app_aplicacion_rol_id)
    # Cambiar estatus a su opuesto
    app_aplicacion_rol.estatus = "B" if app_aplicacion_rol.estatus == "A" else "A"
    app_aplicacion_rol.save()
    # Registrar en la bitácora
    accion = "Activado" if app_aplicacion_rol.estatus == "A" else "Desactivado"
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(
            f"{accion} aplicación-rol {app_aplicacion_rol.app_aplicacion.clave} con el rol {app_aplicacion_rol.rol.nombre}"
        ),
        url=url_for("app_aplicaciones_roles.detail", app_aplicacion_rol_id=app_aplicacion_rol.id),
    )
    bitacora.save()
    # Entregar JSON
    return {
        "success": True,
        "message": "Activo" if app_aplicacion_rol.estatus == "A" else "Inactivo",
        "estatus": app_aplicacion_rol.estatus,
        "id": str(app_aplicacion_rol.id),
    }
