"""Modelo de Documento (tabla `documento`) -- archivo(s) adjuntos a una Solicitud_R.

Columnas del boceto del equipo: id, solicitud_id (FK), nombre, tipo_documento,
creado_por (FK users), creado_at, actualizado_at.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.db_types import GUID


class Documento(Base):
    """Un archivo (contrato, convenio, política) cargado dentro de una solicitud."""

    __tablename__ = "documento"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    solicitud_id = Column(GUID(), ForeignKey("solicitud_r.id"), nullable=False)
    nombre = Column(String, nullable=False)
    tipo_documento = Column(String, nullable=False)
    creado_por = Column(GUID(), ForeignKey("users.id"), nullable=False)
    creado_at = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    solicitud = relationship("SolicitudRevision", back_populates="documentos")
    creador_usuario = relationship("Usuario", foreign_keys=[creado_por])
    versiones = relationship("VersionDocumento", back_populates="documento", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Documento {self.nombre!r} solicitud={self.solicitud_id}>"
