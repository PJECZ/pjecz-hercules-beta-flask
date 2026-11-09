"""
CLI Archivos Documentos
"""

from datetime import datetime
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font
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

# Cantidad máxima de registros a mostrar en la tabla cuando no se da --limit
LIMITE_TABLA = 100

# Columnas: (encabezado, atributo del renglón)
COLUMNAS = [
    ("ID", "id"),
    ("Autoridad", "clave"),
    ("Expediente", "expediente"),
    ("Año", "anio"),
    ("Actor", "actor"),
    ("Demandado", "demandado"),
    ("Juicio", "juicio"),
    ("Tipo", "tipo_juzgado"),
    ("Ubicación", "ubicacion"),
    ("Fojas", "fojas"),
]

# Columnas numéricas, se alinean a la derecha en la tabla
COLUMNAS_NUMERICAS = {"id", "anio", "fojas"}


@arc_documentos.command()
def consultar(
    autoridad_clave: str = Option("", help="Clave de la autoridad"),
    actor: str = Option("", help="Actor (fragmento)"),
    demandado: str = Option("", help="Demandado (fragmento)"),
    expediente: str = Option("", help="Expediente, por ejemplo 123/2024"),
    anio: int = Option(0, help="Año"),
    ubicacion: str = Option("", help=f"Ubicación: {', '.join(ArcDocumento.UBICACIONES)}"),
    limit: Optional[int] = Option(
        None, help=f"Cantidad máxima de registros (tabla: {LIMITE_TABLA} por defecto; XLSX: todos por defecto)"
    ),
    exportar_xlsx: bool = Option(False, "--exportar-xlsx", help="Exportar la consulta a un archivo XLSX"),
    archivo_xlsx: str = Option("", help="Nombre del archivo XLSX (por defecto arc_archivos_YYYY-MM-DD-HHMMSS.xlsx)"),
):
    """Mostrar una tabla con los documentos de archivo, o exportarlos a XLSX"""
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
    if limit is None and not exportar_xlsx:
        limit = LIMITE_TABLA
    if limit is not None:
        if limit <= 0:
            console.print("[red]ERROR: El límite debe ser mayor a cero.")
            raise Exit(code=1)
        stmt = stmt.limit(limit)

    # Si se va a exportar a XLSX
    if exportar_xlsx:
        _exportar_xlsx(console, stmt, archivo_xlsx)
        return

    # Mostrar tabla
    tabla = Table(title="Archivos Documentos")
    for encabezado, atributo in COLUMNAS:
        tabla.add_column(encabezado, justify="right" if atributo in COLUMNAS_NUMERICAS else "left")
    contador = 0
    for item in database.session.execute(stmt):
        tabla.add_row(*[str(getattr(item, atributo) or "") for _, atributo in COLUMNAS])
        contador += 1
    console.print(tabla)
    console.print(f"Se mostraron {contador} documentos.")


def _exportar_xlsx(console: Console, stmt, archivo_xlsx: str):
    """Exportar los renglones de la consulta a un archivo XLSX"""

    # Definir el nombre del archivo
    if archivo_xlsx == "":
        archivo_xlsx = f"arc_archivos_{datetime.now():%Y-%m-%d-%H%M%S}.xlsx"
    elif not archivo_xlsx.lower().endswith(".xlsx"):
        archivo_xlsx += ".xlsx"

    # Crear el libro y la hoja
    libro = Workbook()
    hoja = libro.active

    # Si la hoja es nula, salir
    if hoja is None:
        return
    hoja.title = "Archivos Documentos"

    # Agregar los encabezados en negritas
    hoja.append([encabezado for encabezado, _ in COLUMNAS])
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    hoja.freeze_panes = "A2"

    # Agregar los renglones
    contador = 0
    for item in database.session.execute(stmt):
        hoja.append([getattr(item, atributo) for _, atributo in COLUMNAS])
        contador += 1

    # Ajustar el ancho de las columnas
    for columna in hoja.columns:
        ancho = max(len(str(celda.value)) if celda.value is not None else 0 for celda in columna)
        hoja.column_dimensions[columna[0].column_letter].width = min(ancho + 2, 60)

    # Guardar el archivo
    try:
        libro.save(archivo_xlsx)
    except OSError as error:
        console.print(f"[red]ERROR: No se pudo guardar {archivo_xlsx}: {error}")
        raise Exit(code=1)
    console.print(f"[green]Se exportaron {contador} documentos a {archivo_xlsx}")
