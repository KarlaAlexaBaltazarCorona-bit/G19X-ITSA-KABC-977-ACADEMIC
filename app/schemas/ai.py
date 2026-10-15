"""Esquemas de validación Pydantic para Inteligencia Artificial Jurídica."""

from typing import Any
from pydantic import BaseModel, Field


class LegalQueryRequest(BaseModel):
    """Esquema para realizar una consulta directa al asistente legal de IA."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=3000,
        description="Pregunta o consulta jurídica para el modelo de IA (máximo 3,000 caracteres).",
        examples=["¿Qué cláusulas esenciales debe contener un contrato de prestación de servicios de software?"],
    )
    contexto: str | None = Field(
        default=None,
        max_length=15000,
        description="Contexto legal adicional o fragmento del contrato a analizar (máximo 15,000 caracteres).",
    )


class LegalQueryResponse(BaseModel):
    """Respuesta generada por el modelo de IA."""

    respuesta: str
    modelo: str
    usage: dict[str, Any] | None = None


class RiskAnalysisRequest(BaseModel):
    """Esquema para solicitar el análisis de riesgos de un contrato o texto legal."""

    contract_text: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Texto completo o extracto de las cláusulas del contrato (máximo 50,000 caracteres).",
    )
    tipo_documento: str = Field(
        default="contrato",
        max_length=50,
        description="Tipo de instrumento jurídico (ej. contrato, convenio, politica).",
    )


class RiskAnalysisResponse(BaseModel):
    """Resultado del análisis de riesgos legales estructurado."""

    analisis_detallado: str
    modelo: str
    usage: dict[str, Any] | None = None


class SummarizeRequest(BaseModel):
    """Esquema para solicitar un resumen ejecutivo de un documento legal."""

    contract_text: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Texto del documento a sintetizar (máximo 50,000 caracteres).",
    )


class SummarizeResponse(BaseModel):
    """Resumen ejecutivo del documento."""

    resumen_ejecutivo: str
    modelo: str
    usage: dict[str, Any] | None = None
