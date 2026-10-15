"""Modelo de Versión de Documento (tabla `vercion_documento`).

Columnas: id, documentoID (FK), numero_version,
nombre_archivo, ubicacion, tamaño_archivo, formato_archivo, actualizado_por
(FK users), creado_at.

Se agrega `hash_contenido` para resolver ("que cuando un documento se abra se guarden las
modificaciones para llevar control de versiones"): permite detectar si el
contenido realmente cambió antes de crear una versión nueva, en vez de
duplicar versiones idénticas cada vez que alguien solo abre el archivo.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship, synonym

from app.core.database import Base
from app.core.db_types import GUID


class VersionDocumento(Base):
    """Una versión histórica e inmutable de un `Documento`. Tabla: `vercion_documento`."""

    __tablename__ = "vercion_documento"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    documento_id = Column(GUID(), ForeignKey("documento.id"), nullable=False)
    numero_version = Column(Integer, nullable=False)
    nombre_archivo = Column(String, nullable=False)
    ubicacion = Column(String, nullable=False)  # URL/ruta en Azure Blob Storage
    tamano_archivo = Column(Integer, nullable=True)  # bytes
    formato_archivo = Column(String, nullable=True)  # pdf, docx, etc.
    #ver docstring del módulo.
    hash_contenido = Column(String, nullable=True, index=True)
    actualizado_por = Column(GUID(), ForeignKey("users.id"), nullable=False)
    creado_por = synonym("actualizado_por")
    creado_at = Column(DateTime(timezone=True), server_default=func.now())

    documento = relationship("Documento", back_populates="versiones")
    usuario_actualizo = relationship("Usuario", foreign_keys=[actualizado_por])
    revisiones = relationship("Revision", back_populates="version_documento")
    comentarios = relationship("Comentario", back_populates="version_documento")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<VersionDocumento doc={self.documento_id} v{self.numero_version}>"
