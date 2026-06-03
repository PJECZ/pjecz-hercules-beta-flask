"""
Sentencias, vistas
"""

import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from .models import Sentencia

MODULO = "SENTENCIAS"

sentencias = Blueprint("sentencias", __name__, template_folder="templates")


@sentencias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""
