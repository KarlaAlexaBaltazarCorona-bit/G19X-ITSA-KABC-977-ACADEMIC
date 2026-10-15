"""Modelo de Organización / Tenant.

Esta tabla es un CATÁLOGO INTERNO que el
ADMINISTRADOR_PLATAFORMA puede gestionar desde el panel administrativo
(SQLAdmin) para fines de referencia y reportes. No tiene endpoints propios
activos.
"""

import uuid

from sqlalchemy import Boolean, Column, String

from app.core.database import Base
from app.core.db_types import GUID


class TenantModel(Base):
    """Empresa u organización registrada en el catálogo interno. Tabla: `tenants`."""

    __tablename__ = "tenants"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    nombre_comercial = Column(String, nullable=False)
    rfc = Column(String, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TenantModel {self.nombre_comercial!r}>"
