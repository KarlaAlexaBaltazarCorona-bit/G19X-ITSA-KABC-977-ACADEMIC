"""Modelo de Usuario interno (tabla `users`).

Columnas:
id, objeto_id, correo, nombre, apellido, role, activo, ultima_vez,
creado_at, actualizado_at.
"""

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, String, func
from sqlalchemy.orm import relationship, synonym

from app.core.database import Base
from app.core.db_types import GUID


class RolUsuario(str, enum.Enum):
    """Roles internos del sistema jurídico. No existe rol externo de solicitante."""

    REVISOR_JURIDICO = "REVISOR_JURIDICO"
    APROBADOR_JURIDICO = "APROBADOR_JURIDICO"
    ADMINISTRADOR_PLATAFORMA = "ADMINISTRADOR_PLATAFORMA"
    AUDITOR = "AUDITOR"


class Usuario(Base):
    """Cuenta interna sincronizada con Microsoft Entra ID. Tabla: `users`."""

    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    # "objeto_id" = Object ID (oid) que Microsoft Entra ID asigna a cada
    # cuenta -- identificador estable para reconocer al mismo usuario en cada
    # login, incluso si cambia su correo.
    objeto_id = Column(String, unique=True, index=True, nullable=False)
    correo = Column(String, unique=True, nullable=False, index=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=True)
    role = Column(Enum(RolUsuario), nullable=False, default=RolUsuario.REVISOR_JURIDICO)
    activo = Column(Boolean, default=True, nullable=False)
    ultima_vez = Column(DateTime(timezone=True), nullable=True)  # último login
    creado_at = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    solicitudes_pedidas = relationship(
        "SolicitudRevision", back_populates="solicitante", foreign_keys="SolicitudRevision.requested_id"
    )
    solicitudes_creadas = synonym("solicitudes_pedidas")
    solicitudes_asignadas = relationship(
        "SolicitudRevision", back_populates="revisor", foreign_keys="SolicitudRevision.revicion_id"
    )

    @property
    def nombre_completo(self) -> str:
        """Conveniencia: nombre y apellido juntos, para mostrar en la interfaz."""
        return f"{self.nombre} {self.apellido}".strip() if self.apellido else self.nombre

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Usuario {self.correo} ({self.role})>"
