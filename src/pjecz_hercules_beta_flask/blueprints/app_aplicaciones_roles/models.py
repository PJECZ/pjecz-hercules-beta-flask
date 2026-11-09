"""
App Aplicaciones Roles, modelos
"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class AppAplicacionRol(database.Model, UniversalMixin):
    """AppAplicacionRol"""

    NIVELES = {
        1: "VER",
        2: "VER y MODIFICAR",
        3: "VER, MODIFICAR y CREAR",
        4: "ADMINISTRAR",
    }

    # Nombre de la tabla
    __tablename__ = "app_aplicaciones_roles"
    __table_args__ = (UniqueConstraint("app_aplicacion_id", "rol_id"),)

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Claves foráneas
    app_aplicacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_aplicaciones.id"))
    app_aplicacion: Mapped["AppAplicacion"] = relationship(back_populates="app_aplicaciones_roles")
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    rol: Mapped["Rol"] = relationship(back_populates="app_aplicaciones_roles")

    # Columnas
    nivel: Mapped[int]

    @property
    def nivel_descrito(self):
        """Nivel descrito"""
        return self.NIVELES.get(self.nivel, "")

    def __repr__(self):
        """Representación"""
        return f"<AppAplicacionRol {self.id}>"
