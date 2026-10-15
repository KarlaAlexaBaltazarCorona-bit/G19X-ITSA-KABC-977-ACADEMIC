"""Esquemas de validación Pydantic para Comentarios (HU-06, HU-07)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ComentarioCreate(BaseModel):
    """Esquema de entrada para agregar un comentario u observación a una solicitud."""

    contenido: str = Field(..., min_length=1, max_length=4000)
    vercion_documento_id: uuid.UUID | None = None
    comentario_padre_id: uuid.UUID | None = None


class ComentarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    solicitud_id: uuid.UUID
    vercion_documento_id: uuid.UUID | None = None
    user_id: uuid.UUID
    comentario_padre_id: uuid.UUID | None = None
    contenido: str
    resuelto: bool
    creado_at: datetime | None = None
    resuelto_at: datetime | None = None
