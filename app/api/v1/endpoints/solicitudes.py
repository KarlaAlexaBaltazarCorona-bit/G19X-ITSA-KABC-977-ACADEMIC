"""Módulo de Solicitudes de Revisión (tabla `solicitud_r`) -- el núcleo del workflow.

Cubre HU-01 (gestionar flujo de revisión), HU-04 (consultar documentos
asignados) y, junto con `documents.py`, la carga inicial de un documento
(HU-01/Pantalla 5 "Nuevo documento / Nueva solicitud").
"""

import datetime
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.audit_helper import registrar_auditoria
from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.document import Documento
from app.models.solicitud import EstadoSolicitud, PrioridadSolicitud, SolicitudRevision
from app.models.user import RolUsuario
from app.schemas.solicitud import SolicitudDecision, SolicitudReasignar, SolicitudResponse
from app.services.azure_openai import LegalAIService
from app.services.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)
router = APIRouter()

ROLES_TODOS = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.AUDITOR.value,
)

ROLES_CREACION = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
)


def _puede_ver_solicitud(usuario: dict, solicitud: SolicitudRevision) -> bool:
    """Regla de visibilidad: todos los roles del departamento jurídico y auditoría tienen acceso."""
    return usuario["rol"] in ROLES_TODOS


@router.get("/", response_model=list[SolicitudResponse], summary="Listar solicitudes de revisión")
def list_solicitudes(
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """Lista las solicitudes visibles para los usuarios del área jurídica y auditoría (HU-01, HU-04)."""
    return db.query(SolicitudRevision).order_by(SolicitudRevision.actualizado_at.desc()).all()


@router.post(
    "/",
    response_model=SolicitudResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva solicitud de revisión y cargar el primer documento",
)
async def create_solicitud(
    titulo: str,
    tipo_documento: str,
    archivo: UploadFile,
    descripcion: str | None = None,
    prioridad: PrioridadSolicitud = PrioridadSolicitud.NORMAL,
    fecha_limite: datetime.datetime | None = None,
    enviar_a_revision: bool = True,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_CREACION)),
    request: Request = None,
):
    """Pantalla 5 ("Nuevo documento / Nueva solicitud"): crea la Solicitud_R,
    el Documento y su primera Version_documento en un solo paso, sube el
    archivo a Azure Blob Storage, genera el folio consecutivo (EXP-YYYY-XXXX),
    y si enviar_a_revision es True, dispara la asignación automática de
    revisor (HU-01, HU-03).
    """
    contenido = await archivo.read()
    folio = WorkflowEngine.generar_folio_expediente(db)

    solicitud = SolicitudRevision(
        numero_respuesta=folio,
        titulo=titulo,
        descripcion=descripcion,
        requested_id=usuario["id"],
        tipo_documento=tipo_documento,
        prioridad=prioridad,
        fecha_limite=fecha_limite,
        estado=EstadoSolicitud.BORRADOR,
    )
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    documento = Documento(
        solicitud_id=solicitud.id,
        nombre=archivo.filename or titulo,
        tipo_documento=tipo_documento,
        creado_por=usuario["id"],
    )
    db.add(documento)
    db.commit()
    db.refresh(documento)

    WorkflowEngine.guardar_version_si_cambio(
        db,
        documento,
        contenido=contenido,
        nombre_archivo=archivo.filename or titulo,
        formato_archivo=(archivo.content_type or "application/octet-stream"),
        usuario=usuario,
        request=request,
    )

    # Extracción y guardado en caché de texto para disponibilidad inmediata en el chat de IA
    try:
        from app.services.document_extractor import cache_document_text, extract_text_from_bytes
        texto_extraido = extract_text_from_bytes(
            content=contenido,
            filename=archivo.filename or titulo,
            content_type=archivo.content_type or "",
        )
        if texto_extraido:
            cache_document_text(solicitud.id, texto_extraido)
            cache_document_text(documento.id, texto_extraido)
            try:
                LegalAIService.clasificar_area(texto_extraido)
            except Exception as e_area:
                logger.warning("No se pudo clasificar el área automáticamente: %s", e_area)
    except Exception as e:
        logger.warning("No se pudo extraer texto del documento: %s", e)

    if enviar_a_revision:
        registrar_auditoria(
            db,
            usuario,
            accion=f"Creó el expediente {folio} y cargó el documento {documento.nombre!r}.",
            tipo_documento="solicitud",
            id_documento=solicitud.id,
            solicitud_id=solicitud.id,
            request=request,
        )
        # HU-03: asignación automática de revisor jurídico.
        WorkflowEngine.iniciar_revision(db, solicitud, usuario, request=request)
    else:
        registrar_auditoria(
            db,
            usuario,
            accion=f"Creó el expediente {folio} y guardó la solicitud en estado BORRADOR.",
            tipo_documento="solicitud",
            id_documento=solicitud.id,
            solicitud_id=solicitud.id,
            request=request,
        )

    return solicitud


@router.get("/{solicitud_id}", response_model=SolicitudResponse, summary="Detalle de una solicitud")
def get_solicitud(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    solicitud = db.get(SolicitudRevision, solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")
    if not _puede_ver_solicitud(usuario, solicitud):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta solicitud.")
    return solicitud


@router.post(
    "/{solicitud_id}/enviar",
    response_model=SolicitudResponse,
    summary="Enviar una solicitud en borrador al flujo de revisión jurídica",
)
def enviar_solicitud_a_revision(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_CREACION)),
    request: Request = None,
):
    """Pasa una solicitud de BORRADOR a EN_REVISION y dispara la asignación automática (HU-01, HU-03, RF-003)."""
    solicitud = db.get(SolicitudRevision, solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")
    if not _puede_ver_solicitud(usuario, solicitud):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta solicitud.")
    if solicitud.estado != EstadoSolicitud.BORRADOR:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"La solicitud ya se encuentra en estado {solicitud.estado.value} y no puede enviarse nuevamente.",
        )
    return WorkflowEngine.iniciar_revision(db, solicitud, usuario, request=request)


@router.patch(
    "/{solicitud_id}/reasignar",
    response_model=SolicitudResponse,
    summary="Reasignar manualmente el revisor de una solicitud",
)
def reasignar_solicitud(
    solicitud_id: uuid.UUID,
    payload: SolicitudReasignar,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(RolUsuario.ADMINISTRADOR_PLATAFORMA.value)),
    request: Request = None,
):
    """el Admin puede reasignar a mano cuando el balanceo automático no aplica."""
    solicitud = db.get(SolicitudRevision, solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")
    return WorkflowEngine.reasignar_revisor(db, solicitud, payload.nuevo_revisor_id, usuario, request=request)


@router.post(
    "/{solicitud_id}/decision",
    response_model=SolicitudResponse,
    summary="Aprobar, rechazar o solicitar cambios sobre una solicitud",
)
def decidir_solicitud(
    solicitud_id: uuid.UUID,
    payload: SolicitudDecision,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(RolUsuario.APROBADOR_JURIDICO.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value)),
    request: Request = None,
):
    """Pantalla 9 (Aprobación / Rechazo). `payload.decision` es "aprobar", "rechazar" o "cambios"."""
    solicitud = db.get(SolicitudRevision, solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")

    mapa_decision = {
        "aprobar": EstadoSolicitud.APROBADO,
        "rechazar": EstadoSolicitud.RECHAZADO,
        "cambios": EstadoSolicitud.OBSERVADO,
    }
    nuevo_estado = mapa_decision.get(payload.decision)
    if nuevo_estado is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "decision debe ser 'aprobar', 'rechazar' o 'cambios'.")

    return WorkflowEngine.transicionar_estado(db, solicitud, nuevo_estado, usuario, motivo=payload.motivo, request=request)
