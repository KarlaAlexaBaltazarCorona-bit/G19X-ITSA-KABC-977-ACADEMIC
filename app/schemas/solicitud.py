"""Esquemas de validación Pydantic para Solicitud de Revisión (tabla `solicitud_r`)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.solicitud import EstadoSolicitud, PrioridadSolicitud


class SolicitudCreate(BaseModel):
    """Esquema de entrada para registrar una nueva solicitud de revisión (Pantalla 5)."""

    titulo: str = Field(..., min_length=3, max_length=200)
    descripcion: str | None = None
    tipo_documento: str = Field(..., description="contrato, convenio o politica")
    prioridad: PrioridadSolicitud = PrioridadSolicitud.NORMAL
    fecha_limite: datetime | None = None


class SolicitudResponse(BaseModel):
    """Esquema de salida con los metadatos de una solicitud."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_respuesta: str | None = None
    titulo: str
    descripcion: str | None = None
    requested_id: uuid.UUID
    revicion_id: uuid.UUID | None = None
    tipo_documento: str
    prioridad: PrioridadSolicitud
    estado: EstadoSolicitud
    fecha_limite: datetime | None = None
    creado_at: datetime | None = None
    actualizado_at: datetime | None = None
    finalizo_at: datetime | None = None


class SolicitudReasignar(BaseModel):
    """Esquema de entrada para que un Admin reasigne el revisor."""

    nuevo_revisor_id: uuid.UUID


class SolicitudDecision(BaseModel):
    """Esquema de entrada para aprobar/rechazar/pedir cambios (Pantalla 9)."""

    decision: str = Field(..., description="aprobar | rechazar | cambios")
    motivo: str | None = None
