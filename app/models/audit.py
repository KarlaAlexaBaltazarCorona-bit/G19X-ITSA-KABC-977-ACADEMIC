"""Modelo de Auditoría genérica (tabla `auditoria`) -- HU-12, trazabilidad.

Columnas del boceto del equipo: id, solicitud_id (FK), user_id (FK),
tipo_documento, id_documento, accion, valor_anterior, valor_nuevo,
direccion_ip, usuario_buscador, creada_at.

Es un log GENÉRICO: `tipo_documento` + `id_documento` identifican QUÉ se
modificó (una solicitud, un documento, un comentario, una revisión...), y
`valor_anterior`/`valor_nuevo` guardan el cambio en sí. Así una sola tabla
audita todo el sistema en vez de tener una tabla de auditoría por entidad.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.db_types import GUID


class Auditoria(Base):
    """Una fila = una acción registrada sobre alguna entidad del sistema."""

    __tablename__ = "auditoria"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    solicitud_id = Column(GUID(), ForeignKey("solicitud_r.id"), nullable=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)

    # "tipo_documento" aquí se usa en un sentido amplio: el TIPO de entidad
    # auditada -- p. ej. "solicitud", "documento", "comentario", "revision" --
    # no necesariamente un documento legal.
    tipo_documento = Column(String, nullable=False)
    id_documento = Column(GUID(), nullable=True)  # id de la entidad afectada

    accion = Column(String, nullable=False)
    valor_anterior = Column(Text, nullable=True)
    valor_nuevo = Column(Text, nullable=True)
    direccion_ip = Column(String, nullable=True)
    usuario_buscador = Column(String, nullable=True)  # User-Agent del navegador

    creada_at = Column(DateTime(timezone=True), server_default=func.now())

    solicitud = relationship("SolicitudRevision")
    usuario = relationship("Usuario", foreign_keys=[user_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Auditoria {self.tipo_documento}:{self.id_documento} accion={self.accion!r}>"
