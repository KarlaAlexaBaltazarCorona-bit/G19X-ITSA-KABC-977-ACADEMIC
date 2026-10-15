"""Módulo de Inteligencia Artificial Jurídica (Azure OpenAI, LangChain, Document Intelligence)."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_guard import verify_api_key
from app.core.database import get_db
from app.core.rate_limiter import rate_limit_guard
from app.core.roles_guard import requiere_roles
from app.models.extras import ChatMensaje
from app.models.user import RolUsuario
from app.schemas.ai import (
    LegalQueryRequest,
    LegalQueryResponse,
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services.azure_openai import LegalAIService
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(rate_limit_guard)])


ROLES_TODOS = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.AUDITOR.value,
)

ROLES_REVISION = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
)


@router.post(
    "/query",
    response_model=LegalQueryResponse,
    summary="Consulta directa al Asistente Legal con IA",
    description="Permite realizar preguntas jurídicas directas o sobre un fragmento contractual al modelo gpt-5-mini.",
)
def query_legal_ai(
    payload: LegalQueryRequest,
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """Envía una consulta jurídica a Azure OpenAI."""
    try:
        result = LegalAIService.ask_legal_assistant(
            prompt=payload.prompt,
            context=payload.contexto,
        )
        return result
    except ValueError as ve:
        logger.warning("Configuración de IA no disponible: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de análisis de IA temporalmente no disponible.",
        ) from ve
    except Exception as e:
        logger.error("Error al procesar consulta con Azure OpenAI: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al procesar la solicitud con el motor de IA.",
        ) from e


@router.post(
    "/risk-analysis",
    response_model=RiskAnalysisResponse,
    summary="Detección y dictamen de riesgos jurídicos con IA",
    description="Analiza cláusulas y texto de contratos para detectar riesgos, penalizaciones abusivas y redactar recomendaciones.",
)
def analyze_risks(
    payload: RiskAnalysisRequest,
    usuario: dict = Depends(requiere_roles(*ROLES_REVISION)),
):
    """Ejecuta una auditoría de riesgos contractuales con Azure OpenAI."""
    try:
        result = LegalAIService.analyze_legal_risks(
            contract_text=payload.contract_text,
            doc_type=payload.tipo_documento,
        )
        return result
    except ValueError as ve:
        logger.warning("Configuración de IA no disponible: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de análisis de IA temporalmente no disponible.",
        ) from ve
    except Exception as e:
        logger.error("Error al procesar auditoría de riesgos: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al procesar la auditoría de riesgos con el motor de IA.",
        ) from e


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    summary="Resumen ejecutivo estructurado del contrato",
    description="Sintetiza partes, vigencia, obligaciones y jurisdicción de cualquier instrumento jurídico.",
)
def summarize_contract(
    payload: SummarizeRequest,
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """Genera un resumen ejecutivo del documento legal."""
    try:
        result = LegalAIService.summarize_contract(
            contract_text=payload.contract_text,
        )
        return result
    except ValueError as ve:
        logger.warning("Configuración de IA no disponible: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de análisis de IA temporalmente no disponible.",
        ) from ve
    except Exception as e:
        logger.error("Error al procesar resumen ejecutivo: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al procesar el resumen ejecutivo con el motor de IA.",
        ) from e


@router.post("/extract-clauses", summary="Extracción OCR de cláusulas")
def extract_clauses(usuario: dict = Depends(requiere_roles(*ROLES_REVISION))):
    """Cascarón para procesamiento con Azure AI Document Intelligence."""
    return {"message": "Endpoint en desarrollo."}


# ------------------------------------------------------------------
# "Chat -- panel a lado derecho para anotar especificaciones"
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Esquema de entrada para una pregunta al chat de IA de una solicitud."""

    pregunta: str = Field(..., min_length=1, max_length=3000)


class ChatMensajeResponse(BaseModel):
    """Un mensaje del historial del chat de IA de una solicitud."""

    id: uuid.UUID
    rol_mensaje: str
    contenido: str

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/chat/{solicitud_id}",
    response_model=list[ChatMensajeResponse],
    summary="Historial del chat de IA de una solicitud",
    dependencies=[Depends(requiere_roles(
        RolUsuario.REVISOR_JURIDICO.value, RolUsuario.APROBADOR_JURIDICO.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value
    ))],
)
def obtener_historial_chat(solicitud_id: uuid.UUID, db: Session = Depends(get_db)):
    """Devuelve toda la conversación guardada para el panel de chat."""
    return (
        db.query(ChatMensaje)
        .filter(ChatMensaje.solicitud_id == solicitud_id)
        .order_by(ChatMensaje.creado_at.asc())
        .all()
    )


@router.post(
    "/chat/{solicitud_id}",
    response_model=ChatMensajeResponse,
    summary="Enviar una pregunta al chat de IA sobre una solicitud",
)
def chat_sobre_solicitud(
    solicitud_id: uuid.UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(
        RolUsuario.REVISOR_JURIDICO.value, RolUsuario.APROBADOR_JURIDICO.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value
    )),
):
    """Convierte el panel estático de "Análisis con IA" en un chat real y con memoria
    por solicitud. Guarda tanto la pregunta como la respuesta.
    """
    historial_previo = (
        db.query(ChatMensaje)
        .filter(ChatMensaje.solicitud_id == solicitud_id)
        .order_by(ChatMensaje.creado_at.asc())
        .all()
    )
    historial_para_ia = [{"rol_mensaje": m.rol_mensaje, "contenido": m.contenido} for m in historial_previo]

    mensaje_usuario = ChatMensaje(
        solicitud_id=solicitud_id, autor_id=usuario["id"], rol_mensaje="usuario", contenido=payload.pregunta
    )
    db.add(mensaje_usuario)
    db.commit()

    contexto_doc = ""
    try:
        from app.models.document import Documento
        from app.models.solicitud import SolicitudRevision
        from app.services.document_extractor import get_document_text_for_solicitud

        sol = db.query(SolicitudRevision).filter(SolicitudRevision.id == solicitud_id).first()
        doc = db.query(Documento).filter(Documento.solicitud_id == solicitud_id).first()

        meta_parts = []
        if sol:
            meta_parts.append(f"Expediente/Título: '{sol.titulo}' (Tipo: {sol.tipo_documento}, Prioridad: {sol.prioridad.value if hasattr(sol.prioridad, 'value') else sol.prioridad})")
        if doc:
            meta_parts.append(f"Archivo adjunto: {doc.nombre}")
            if doc.versiones:
                ult_ver = doc.versiones[-1]
                meta_parts.append(f"Versión: v{ult_ver.numero_version} ({ult_ver.nombre_archivo})")

        contexto_doc = " | ".join(meta_parts)

        # Extraer y adjuntar el texto íntegro del documento para que la IA lo analice realmente
        texto_real = get_document_text_for_solicitud(db, solicitud_id)
        if texto_real:
            contexto_doc += f"\n\n--- CONTENIDO TEXTUAL DEL INSTRUMENTO LEGAL BAJO REVISIÓN ---\n{texto_real}"
        else:
            logger.info("No se encontró texto digitalizado para la solicitud %s", solicitud_id)
    except Exception as err:
        logger.warning("No se pudo obtener el texto o metadatos de documento para contexto de chat: %s", err)

    try:
        respuesta_texto = LegalAIService.responder_con_contexto(
            historial=historial_para_ia,
            pregunta=payload.pregunta,
            contexto_documento=contexto_doc,
        )
    except ValueError as ve:
        logger.warning("Configuración de IA no disponible para el chat: %s", ve)
        respuesta_texto = "Servicio de Inteligencia Artificial temporalmente no disponible (verifique las credenciales de Azure OpenAI)."
    except Exception as e:
        logger.error("Error al generar respuesta en el chat de IA: %s", e, exc_info=True)
        respuesta_texto = f"Disculpe, ocurrió una incidencia al consultar el motor de IA ({str(e)[:120]}). Intente nuevamente en unos instantes."

    mensaje_asistente = ChatMensaje(
        solicitud_id=solicitud_id, autor_id=None, rol_mensaje="asistente", contenido=respuesta_texto
    )
    db.add(mensaje_asistente)
    db.commit()
    db.refresh(mensaje_asistente)
    return mensaje_asistente

