"""
App Aplicaciones Bitácoras, modelos
"""

import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class AppAplicacionBitacora(database.Model, UniversalMixin):
    """AppAplicacionBitacora"""

    PETICIONES = {
        "GET": "GET",
        "POST": "POST",
        "PUT": "PUT",
        "PATCH": "PATCH",
        "DELETE": "DELETE",
    }

    # Nombre de la tabla
    __tablename__ = "app_aplicaciones_bitacoras"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Claves foráneas
    app_aplicacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_aplicaciones.id"), index=True)
    app_aplicacion: Mapped["AppAplicacion"] = relationship(back_populates="app_aplicaciones_bitacoras")

    # Columnas
    ruta: Mapped[str] = mapped_column(String(512))
    peticion: Mapped[str] = mapped_column(
        Enum(*PETICIONES, name="app_aplicaciones_bitacoras_peticiones", native_enum=False),
        index=True,
    )
    respuesta_estado: Mapped[int] = mapped_column(index=True)
    respuesta_mensaje: Mapped[str] = mapped_column(String(256), default="")

    @property
    def es_exitosa(self):
        """Es exitosa si el código de estado de la respuesta es menor a 400"""
        return self.respuesta_estado is not None and self.respuesta_estado < 400

    def __repr__(self):
        """Representación"""
        return f"<AppAplicacionBitacora {self.id}>"
