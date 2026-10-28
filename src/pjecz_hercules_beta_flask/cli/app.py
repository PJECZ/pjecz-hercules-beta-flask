"""
PJECZ Hercules Beta Flask CLI
"""

from typer import Typer

from pjecz_hercules_beta_flask.cli.commands.autoridades import autoridades
from pjecz_hercules_beta_flask.cli.commands.db import db
from pjecz_hercules_beta_flask.cli.commands.modulos import modulos
from pjecz_hercules_beta_flask.cli.commands.ofi_documentos import ofi_documentos
from pjecz_hercules_beta_flask.cli.commands.ofi_plantillas import ofi_plantillas
from pjecz_hercules_beta_flask.cli.commands.usuarios import usuarios

cli = Typer()
cli.add_typer(autoridades, name="autoridades")
cli.add_typer(db, name="db")
cli.add_typer(modulos, name="modulos")
cli.add_typer(ofi_documentos, name="ofi_documentos")
cli.add_typer(ofi_plantillas, name="ofi_plantillas")
cli.add_typer(usuarios, name="usuarios")

if __name__ == "__main__":
    cli()
