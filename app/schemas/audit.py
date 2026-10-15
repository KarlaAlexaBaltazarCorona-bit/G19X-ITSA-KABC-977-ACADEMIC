"""Esquemas de validación Pydantic para Auditoría (HU-12) y extras (Firma/Notificación)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditoriaResponse(BaseModel):
    """Una entrada de la línea de tiempo de auditoría."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    solicitud_id: uuid.UUID | None = None
    user_id: uuid.UUID
    tipo_documento: str
    id_documento: uuid.UUID | None = None
    accion: str
    valor_anterior: str | None = None
    valor_nuevo: str | None = None
    creada_at: datetime | None = None


class NotificacionResponse(BaseModel):
    """Una alerta pendiente para el usuario autenticado (tabla extra `notificaciones`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    detalle: str | None = None
    leida: bool
    creado_at: datetime | None = None


class FirmaResponse(BaseModel):
    """Estado de la firma electrónica de una solicitud (tabla extra `firmas`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    solicitud_id: uuid.UUID
    firmante_id: uuid.UUID
    estado: str
    firma_detectada_en_documento: str
    firmado_at: datetime | None = None
