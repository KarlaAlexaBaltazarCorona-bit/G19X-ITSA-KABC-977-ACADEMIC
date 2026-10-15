"""Modelo de Revisión (tabla `revicion`) -- el acto de revisar hecho por un abogado.

Columnas del boceto del equipo: id, solicitud_id (FK), revizado_id (FK users),
vercion_documento_id (FK), estado, decision, notas, empezado_at, completado_at.

Nota: se conserva el nombre `revizado_id`.
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.db_types import GUID


class EstadoRevision(str, enum.Enum):
    """Estado de una revisión individual (distinto del estado general de la Solicitud_R)."""

    PENDIENTE = "PENDIENTE"
    EN_PROGRESO = "EN_PROGRESO"
    COMPLETADA = "COMPLETADA"


class DecisionRevision(str, enum.Enum):
    """Dictamen que deja el revisor/aprobador al completar su revisión."""

    SIN_DECISION = "SIN_DECISION"
    APROBAR = "APROBAR"
    SOLICITAR_CAMBIOS = "SOLICITAR_CAMBIOS"
    RECHAZAR = "RECHAZAR"


class Revision(Base):
    """Una revisión (o aprobación) concreta sobre una versión de documento. Tabla: `revicion`."""

    __tablename__ = "revicion"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    solicitud_id = Column(GUID(), ForeignKey("solicitud_r.id"), nullable=False)
    revizado_id = Column(GUID(), ForeignKey("users.id"), nullable=False)  # quién revisó
    vercion_documento_id = Column(GUID(), ForeignKey("vercion_documento.id"), nullable=False)

    estado = Column(Enum(EstadoRevision), default=EstadoRevision.PENDIENTE, nullable=False)
    decision = Column(Enum(DecisionRevision), default=DecisionRevision.SIN_DECISION, nullable=False)
    notas = Column(Text, nullable=True)

    empezado_at = Column(DateTime(timezone=True), server_default=func.now())
    completado_at = Column(DateTime(timezone=True), nullable=True)

    solicitud = relationship("SolicitudRevision", back_populates="revisiones")
    version_documento = relationship("VersionDocumento", back_populates="revisiones")
    revisor_usuario = relationship("Usuario", foreign_keys=[revizado_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Revision solicitud={self.solicitud_id} estado={self.estado}>"
