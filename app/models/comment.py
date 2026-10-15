"""Modelo de Comentarios (tabla `comentarios`), con respuestas anidadas.

Columnas del boceto del equipo: id, solicitud_id (FK), vercion_documento_id
(FK), user_id (FK), comentario_par_id (FK, self-referencial), contenido,
resuelto, creado_at, actualizado_at, resuelto_at.

Cubre HU-06 (agregar comentario) y HU-07 (consultar comentarios).
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship, synonym

from app.core.database import Base
from app.core.db_types import GUID


class Comentario(Base):
    """Un comentario u observación sobre una solicitud/versión, con hilo de respuestas."""

    __tablename__ = "comentarios"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    solicitud_id = Column(GUID(), ForeignKey("solicitud_r.id"), nullable=False)
    vercion_documento_id = Column(GUID(), ForeignKey("vercion_documento.id"), nullable=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    comentario_padre_id = Column(GUID(), ForeignKey("comentarios.id"), nullable=True)
    comentario_par_id = synonym("comentario_padre_id")

    contenido = Column(Text, nullable=False)
    resuelto = Column(Boolean, default=False, nullable=False)

    creado_at = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resuelto_at = Column(DateTime(timezone=True), nullable=True)

    solicitud = relationship("SolicitudRevision", back_populates="comentarios")
    version_documento = relationship("VersionDocumento", back_populates="comentarios")
    usuario = relationship("Usuario", foreign_keys=[user_id])
    respuestas = relationship("Comentario", backref="padre", remote_side=[id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Comentario solicitud={self.solicitud_id} user={self.user_id}>"
