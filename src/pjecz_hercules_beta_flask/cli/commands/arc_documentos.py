"""
CLI Archivos Documentos
"""

from datetime import date, datetime
from pathlib import Path
from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from rich.console import Console
from rich.table import Table
from sqlalchemy import select
from typer import Argument, Exit, Option, Typer

from pjecz_hercules_beta_flask.blueprints.arc_documentos.models import ArcDocumento
from pjecz_hercules_beta_flask.blueprints.arc_documentos_tipos.models import ArcDocumentoTipo
from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.safe_string import (
    extract_expediente_anio,
    extract_expediente_num,
    safe_clave,
    safe_expediente,
    safe_string,
)
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
        except IndexError, ValueError:
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


class RenglonInvalido(ValueError):
    """Error de validación de un renglón del XLSX"""


def _texto(valor, max_len: int, obligatorio: bool, nombre: str) -> str:
    """Limpiar un texto de una celda, recortando a max_len"""
    texto = safe_string(str(valor) if valor is not None else "", max_len=0, save_enie=True)
    if obligatorio and texto == "":
        raise RenglonInvalido(f"{nombre} está vacío")
    return texto[:max_len]


def _entero(valor, nombre: str) -> int:
    """Convertir una celda a entero"""
    if isinstance(valor, bool):
        raise RenglonInvalido(f"{nombre} no es un número: {valor}")
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    try:
        return int(str(valor).strip())
    except TypeError, ValueError:
        raise RenglonInvalido(f"{nombre} no es un número: {valor}")


def _validar_renglon(celdas: tuple, autoridades: dict[str, int]) -> dict:
    """Validar las celdas de un renglón y entregar los valores limpios"""

    # Completar con None si el renglón trae menos columnas
    celdas = tuple(celdas) + (None,) * (len(COLUMNAS) - len(celdas))
    _, autoridad_clave, expediente, anio, actor, demandado, juicio, tipo_juzgado, ubicacion, fojas = celdas[: len(COLUMNAS)]

    # Autoridad
    autoridad_clave = safe_clave(str(autoridad_clave) if autoridad_clave is not None else "")
    if autoridad_clave == "":
        raise RenglonInvalido("la clave de la autoridad está vacía")
    if autoridad_clave not in autoridades:
        raise RenglonInvalido(f"no existe la autoridad {autoridad_clave}")

    # Expediente
    try:
        expediente = safe_expediente(str(expediente) if expediente is not None else "")
    except IndexError, ValueError:
        raise RenglonInvalido(f"el expediente no es válido: {expediente}")
    if expediente == "":
        raise RenglonInvalido("el expediente está vacío")

    # Año, debe coincidir con el año del expediente
    anio = _entero(anio, "el año")
    if anio < 1900 or anio > date.today().year:
        raise RenglonInvalido(f"el año está fuera de rango: {anio}")
    if anio != extract_expediente_anio(expediente):
        raise RenglonInvalido(f"el año {anio} no coincide con el del expediente {expediente}")

    # Tipo de juzgado
    tipo_juzgado = safe_string(str(tipo_juzgado) if tipo_juzgado is not None else "")
    if tipo_juzgado not in ArcDocumento.TIPO_JUZGADOS:
        raise RenglonInvalido(f"el tipo debe ser {' o '.join(ArcDocumento.TIPO_JUZGADOS)}: {tipo_juzgado}")

    # Ubicación, si viene vacía es NO DEFINIDO
    ubicacion = safe_string(str(ubicacion) if ubicacion is not None else "") or "NO DEFINIDO"
    if ubicacion not in ArcDocumento.UBICACIONES:
        raise RenglonInvalido(f"la ubicación debe ser una de {', '.join(ArcDocumento.UBICACIONES)}: {ubicacion}")

    # Fojas
    fojas = _entero(fojas, "las fojas")
    if fojas < 0:
        raise RenglonInvalido(f"las fojas no pueden ser negativas: {fojas}")

    return {
        "autoridad_id": autoridades[autoridad_clave],
        "expediente": expediente,
        "expediente_numero": extract_expediente_num(expediente),
        "anio": anio,
        "actor": _texto(actor, 256, False, "el actor"),
        "demandado": _texto(demandado, 256, False, "el demandado"),
        "juicio": _texto(juicio, 128, False, "el juicio"),
        "tipo_juzgado": tipo_juzgado,
        "ubicacion": ubicacion,
        "fojas": fojas,
    }


@arc_documentos.command()
def alimentar(
    archivo_xlsx: Path = Argument(..., exists=True, dir_okay=False, readable=True, help="Archivo XLSX a cargar"),
    probar: bool = Option(False, "--probar", help="Validar y contar sin hacer cambios en la base de datos"),
):
    """Insertar o actualizar documentos de archivo a partir de un archivo XLSX"""
    console = Console()
    console.print(f"Alimentando los documentos de archivo desde {archivo_xlsx}...")
    if probar:
        console.print("[yellow]Modo de prueba: no se harán cambios en la base de datos.")

    # Abrir el archivo XLSX
    try:
        libro = load_workbook(archivo_xlsx, read_only=True, data_only=True)
    except Exception as error:
        console.print(f"[red]ERROR: No se pudo abrir {archivo_xlsx}: {error}")
        raise Exit(code=1)
    hoja = libro.active
    if hoja is None:
        console.print("[red]ERROR: El archivo XLSX no tiene hojas.")
        raise Exit(code=1)

    # Cargar las claves de las autoridades
    autoridades = {
        clave: autoridad_id for autoridad_id, clave in database.session.execute(select(Autoridad.id, Autoridad.clave))
    }

    # Consultar el tipo de documento NO DEFINIDO, para los nuevos
    arc_documento_tipo_id = database.session.execute(
        select(ArcDocumentoTipo.id).filter(ArcDocumentoTipo.nombre == "NO DEFINIDO")
    ).scalar_one_or_none()
    if arc_documento_tipo_id is None:
        console.print("[red]ERROR: No existe el tipo de documento NO DEFINIDO.")
        raise Exit(code=1)

    # Columnas que se actualizan en los documentos existentes
    columnas_a_actualizar = ["expediente_numero", "anio", "actor", "demandado", "juicio", "tipo_juzgado", "ubicacion", "fojas"]

    # Recorrer los renglones, el primero son los encabezados
    insertados = 0
    actualizados = 0
    sin_cambios = 0
    invalidos = 0
    try:
        for numero, celdas in enumerate(hoja.iter_rows(min_row=2, values_only=True), start=2):
            # Omitir los renglones vacíos
            if all(celda is None or str(celda).strip() == "" for celda in celdas):
                continue

            # Validar
            try:
                datos = _validar_renglon(celdas, autoridades)
            except RenglonInvalido as error:
                console.print(f"[red]Renglón {numero}: {error}")
                invalidos += 1
                continue

            # Consultar si ya existen documentos con esa autoridad y expediente
            existentes = (
                database.session.execute(
                    select(ArcDocumento)
                    .filter(ArcDocumento.autoridad_id == datos["autoridad_id"])
                    .filter(ArcDocumento.expediente == datos["expediente"])
                    .filter(ArcDocumento.estatus == "A")
                )
                .scalars()
                .all()
            )

            # Si no existe, insertar
            if not existentes:
                database.session.add(
                    ArcDocumento(
                        **datos,
                        arc_documento_tipo_id=arc_documento_tipo_id,
                        arc_juzgados_origen_claves="",
                    )
                )
                insertados += 1
                continue

            # Si existen, actualizar todos los que coincidan
            for arc_documento in existentes:
                hay_cambios = False
                for columna in columnas_a_actualizar:
                    if getattr(arc_documento, columna) != datos[columna]:
                        setattr(arc_documento, columna, datos[columna])
                        hay_cambios = True
                if hay_cambios:
                    actualizados += 1
                else:
                    sin_cambios += 1

        # Guardar todo en una sola transacción, o deshacer si es prueba
        if probar:
            database.session.rollback()
        else:
            database.session.commit()
    except Exception:
        database.session.rollback()
        console.print("[red]ERROR: Se deshicieron todos los cambios.")
        raise
    finally:
        libro.close()

    # Mostrar los contadores
    prefijo = "Se insertarían" if probar else "Se insertaron"
    console.print(f"[green]{prefijo} {insertados} documentos.")
    prefijo = "Se actualizarían" if probar else "Se actualizaron"
    console.print(f"[green]{prefijo} {actualizados} documentos.")
    console.print(f"Sin cambios: {sin_cambios} documentos.")
    if invalidos:
        console.print(f"[red]Renglones inválidos (omitidos): {invalidos}")
