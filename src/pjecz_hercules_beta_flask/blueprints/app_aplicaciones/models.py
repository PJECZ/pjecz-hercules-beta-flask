"""
App Aplicaciones, modelos
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.blueprints.app_aplicaciones_roles.models import AppAplicacionRol
from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class AppAplicacion(database.Model, UniversalMixin):
    """AppAplicacion"""

    # Nombre de la tabla
    __tablename__ = "app_aplicaciones"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    cuota_diaria: Mapped[int] = mapped_column(default=1000)
    cuota_por_hora: Mapped[int] = mapped_column(default=100)

    # Columnas que NO deben ser expuestas
    api_key: Mapped[Optional[str]] = mapped_column(String(128))
    expiracion: Mapped[Optional[datetime]]

    # Hijos
    app_aplicaciones_roles: Mapped[list["AppAplicacionRol"]] = relationship(back_populates="app_aplicacion")

    @property
    def api_key_oculta(self):
        """API key oculta, solo muestra los primeros cuatro caracteres"""
        if not self.api_key:
            return ""
        return self.api_key[:4] + "*" * 12

    def __repr__(self):
        """Representación"""
        return f"<AppAplicacion {self.id}>"
