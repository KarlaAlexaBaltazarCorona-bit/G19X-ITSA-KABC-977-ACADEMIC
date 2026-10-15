"""Modelo de Solicitud de Revisión (tabla `solicitud_r`).

Cubre HU-01 (gestionar flujo de revisión), HU-02/HU-04 (bandeja de trabajo:
"mis solicitudes asignadas") y HU-03 (asignación automática vía `revicion_id`).
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship, synonym

from app.core.database import Base
from app.core.db_types import GUID


class EstadoSolicitud(str, enum.Enum):
    """Ciclo de vida de una solicitud de revisión."""

    BORRADOR = "BORRADOR"
    EN_REVISION = "EN_REVISION"
    OBSERVADO = "OBSERVADO"
    EN_APROBACION = "EN_APROBACION"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    FIRMADO = "FIRMADO"


class PrioridadSolicitud(str, enum.Enum):
    """Prioridad de la solicitud de revisión."""

    BAJA = "BAJA"
    NORMAL = "NORMAL"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


class SolicitudRevision(Base):
    """Una solicitud de revisión jurídica. Tabla: `solicitud_r`.

    Columnas: id, numero_respuesta,
    titulo, descripcion, requested_id (FK users), revicion_id (FK users),
    tipo_documento, prioridad, estado, fecha_limite, creado_at,
    actualizado_at, finalizo_at.
    """

    __tablename__ = "solicitud_r"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    # Nombre de columna.
    numero_respuesta = Column(String, unique=True, nullable=True, index=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)

    # Quién creó o registró la solicitud de revisión (FK a users.id).
    requested_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    # A quién quedó asignada la revisión (FK a users.id).
    # Nulo mientras está en BORRADOR / sin asignar todavía.
    revicion_id = Column(GUID(), ForeignKey("users.id"), nullable=True)

    tipo_documento = Column(String, nullable=False)  # contrato, convenio, politica
    prioridad = Column(Enum(PrioridadSolicitud), default=PrioridadSolicitud.NORMAL, nullable=False)
    estado = Column(Enum(EstadoSolicitud), default=EstadoSolicitud.BORRADOR, nullable=False)
    fecha_limite = Column(DateTime(timezone=True), nullable=True)

    creado_at = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    finalizo_at = Column(DateTime(timezone=True), nullable=True)

    solicitante = relationship("Usuario", back_populates="solicitudes_pedidas", foreign_keys=[requested_id])
    creador = synonym("solicitante")
    solicitado_por = synonym("solicitante")
    revisor = relationship("Usuario", back_populates="solicitudes_asignadas", foreign_keys=[revicion_id])

    documentos = relationship("Documento", back_populates="solicitud", cascade="all, delete-orphan")
    revisiones = relationship("Revision", back_populates="solicitud", cascade="all, delete-orphan")
    comentarios = relationship("Comentario", back_populates="solicitud", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SolicitudRevision {self.titulo!r} ({self.estado})>"
