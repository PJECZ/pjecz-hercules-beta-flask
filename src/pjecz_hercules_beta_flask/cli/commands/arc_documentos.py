"""
CLI Archivos Documentos
"""

from rich.console import Console
from rich.table import Table
from sqlalchemy import select
from typer import Exit, Option, Typer

from pjecz_hercules_beta_flask.blueprints.arc_documentos.models import ArcDocumento
from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_expediente, safe_string
from pjecz_hercules_beta_flask.main import app

# Inicializar la aplicación
# app = create_app()
app.app_context().push()

arc_documentos = Typer()


@arc_documentos.command()
def consultar(
    autoridad_clave: str = Option("", help="Clave de la autoridad"),
    actor: str = Option("", help="Actor (fragmento)"),
    demandado: str = Option("", help="Demandado (fragmento)"),
    expediente: str = Option("", help="Expediente, por ejemplo 123/2024"),
    anio: int = Option(0, help="Año"),
    ubicacion: str = Option("", help=f"Ubicación: {', '.join(ArcDocumento.UBICACIONES)}"),
    limit: int = Option(100, help="Cantidad máxima de registros"),
):
    """Mostrar una tabla con los documentos de archivo"""
    console = Console()
    console.print("Consultando los documentos de archivo...")

    # Preparar la consulta
    stmt = (
        select(
            ArcDocumento.id,
            Autoridad.clave,
            ArcDocumento.expediente,
            ArcDocumento.anio,
            ArcDocumento.actor,
            ArcDocumento.demandado,
            ArcDocumento.juicio,
            ArcDocumento.tipo_juzgado,
            ArcDocumento.ubicacion,
            ArcDocumento.fojas,
        )
        .select_from(
            ArcDocumento,
        )
        .join(
            Autoridad,
        )
    )

    # Solo los que tengan estatus A
    stmt = stmt.filter(ArcDocumento.estatus == "A")

    # Filtrar por la clave de la autoridad
    if autoridad_clave:
        autoridad_clave = safe_clave(autoridad_clave)
        if autoridad_clave == "":
            console.print("[red]ERROR: La clave de la autoridad no es válida.")
            raise Exit(code=1)
        stmt = stmt.filter(Autoridad.clave == autoridad_clave)

    # Filtrar por el actor
    if actor:
        actor = safe_string(actor, save_enie=True)
        if actor != "":
            stmt = stmt.filter(ArcDocumento.actor.contains(actor))

    # Filtrar por el demandado
    if demandado:
        demandado = safe_string(demandado, save_enie=True)
        if demandado != "":
            stmt = stmt.filter(ArcDocumento.demandado.contains(demandado))

    # Filtrar por el expediente
    if expediente:
        try:
            expediente = safe_expediente(expediente)
        except (IndexError, ValueError):
            console.print("[red]ERROR: El expediente no es válido.")
            raise Exit(code=1)
        stmt = stmt.filter(ArcDocumento.expediente == expediente)

    # Filtrar por el año
    if anio:
        stmt = stmt.filter(ArcDocumento.anio == anio)

    # Filtrar por la ubicación
    if ubicacion:
        ubicacion = safe_string(ubicacion)
        if ubicacion not in ArcDocumento.UBICACIONES:
            console.print(f"[red]ERROR: La ubicación debe ser una de: {', '.join(ArcDocumento.UBICACIONES)}")
            raise Exit(code=1)
        stmt = stmt.filter(ArcDocumento.ubicacion == ubicacion)

    # Ordenar por autoridad, año y número de expediente
    stmt = stmt.order_by(Autoridad.clave, ArcDocumento.anio, ArcDocumento.expediente_numero)

    # Limitar la cantidad de registros
    stmt = stmt.limit(limit)

    # Mostrar tabla
    tabla = Table(title="Archivos Documentos")
    tabla.add_column("ID", justify="right")
    tabla.add_column("Autoridad")
    tabla.add_column("Expediente")
    tabla.add_column("Año", justify="right")
    tabla.add_column("Actor")
    tabla.add_column("Demandado")
    tabla.add_column("Juicio")
    tabla.add_column("Tipo")
    tabla.add_column("Ubicación")
    tabla.add_column("Fojas", justify="right")
    contador = 0
    for item in database.session.execute(stmt):
        tabla.add_row(
            str(item.id),
            item.clave,
            item.expediente,
            str(item.anio),
            item.actor,
            item.demandado,
            item.juicio,
            item.tipo_juzgado,
            item.ubicacion,
            str(item.fojas),
        )
        contador += 1
    console.print(tabla)
    console.print(f"Se mostraron {contador} documentos.")
