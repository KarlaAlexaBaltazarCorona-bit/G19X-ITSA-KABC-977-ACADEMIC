"""Esquemas de validación Pydantic para Documentos (tabla `documento`)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """Metadatos que acompañan la carga de un archivo dentro de una solicitud."""

    nombre: str = Field(..., min_length=1, max_length=200)
    tipo_documento: str = Field(..., description="contrato, convenio o politica")


class DocumentResponse(BaseModel):
    """Esquema de salida con los metadatos de un documento."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    solicitud_id: uuid.UUID
    nombre: str
    tipo_documento: str
    creado_por: uuid.UUID
    creado_at: datetime | None = None
    actualizado_at: datetime | None = None


class VersionDocumentoResponse(BaseModel):
    """Una versión guardada de un documento."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    documento_id: uuid.UUID
    numero_version: int
    nombre_archivo: str
    ubicacion: str
    tamano_archivo: int | None = None
    formato_archivo: str | None = None
    actualizado_por: uuid.UUID
    creado_at: datetime | None = None
