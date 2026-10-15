"""Esquemas de validación Pydantic para Revisión (tabla `revicion`)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.revision import DecisionRevision, EstadoRevision


class RevisionCreate(BaseModel):
    """Esquema de entrada para registrar el resultado de una revisión (Pantalla 6)."""

    vercion_documento_id: uuid.UUID | None = None
    documento_id: uuid.UUID | None = None
    decision: DecisionRevision = DecisionRevision.SIN_DECISION
    notas: str | None = Field(default=None, max_length=4000)


class RevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    solicitud_id: uuid.UUID
    revizado_id: uuid.UUID
    vercion_documento_id: uuid.UUID
    estado: EstadoRevision
    decision: DecisionRevision
    notas: str | None = None
    empezado_at: datetime | None = None
    completado_at: datetime | None = None
