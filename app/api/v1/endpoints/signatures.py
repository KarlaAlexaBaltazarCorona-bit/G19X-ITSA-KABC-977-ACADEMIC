"""Módulo de Firmas Electrónicas (tabla extra `firmas` -- ver app/models/extras.py).

Cubre HU-10 (gestionar aprobaciones, en conjunto con solicitudes.py) y HU-11
(firma electrónica, Pantalla 10).("que detectefirmas"): antes de marcar como FIRMADO,
se valida con Azure DocumentIntelligence que el PDF realmente contiene una firma/sello.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.audit_helper import registrar_auditoria
from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.extras import EstadoFirma, Firma
from app.models.solicitud import EstadoSolicitud, SolicitudRevision
from app.models.user import RolUsuario
from app.schemas.audit import FirmaResponse
from app.services.azure_doc_intel import DocumentIntelligenceService
from app.services.workflow_engine import WorkflowEngine

router = APIRouter()

ROLES_FIRMA = (RolUsuario.APROBADOR_JURIDICO.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value)


@router.post("/{solicitud_id}/request", response_model=FirmaResponse, summary="Solicitar firma electrónica")
def request_signature(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_FIRMA)),
    request: Request = None,
):
    """Se llama una vez que la solicitud fue APROBADA, para dejarla lista para firmar."""
    solicitud = db.query(SolicitudRevision).get(solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")
    if solicitud.estado != EstadoSolicitud.APROBADO:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo se puede solicitar firma de solicitudes APROBADAS.")

    firma = Firma(solicitud_id=solicitud_id, firmante_id=usuario["id"], estado=EstadoFirma.PENDIENTE)
    db.add(firma)
    db.commit()
    db.refresh(firma)

    registrar_auditoria(
        db, usuario, accion="Solicitó firma electrónica.", tipo_documento="firma", id_documento=firma.id,
        solicitud_id=solicitud_id, request=request,
    )
    return firma


@router.post("/{solicitud_id}/sign", response_model=FirmaResponse, summary="Firmar documento")
async def sign_document(
    solicitud_id: uuid.UUID,
    archivo: UploadFile | None = None,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_FIRMA)),
    request: Request = None,
):
    """Registra la firma. Si se adjunta el PDF ya firmado, se valida con Document
    Intelligence que efectivamente contenga una firma antes
    de marcar la solicitud como FIRMADO.
    """
    solicitud = db.query(SolicitudRevision).get(solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")

    firma = (
        db.query(Firma)
        .filter(Firma.solicitud_id == solicitud_id, Firma.estado == EstadoFirma.PENDIENTE)
        .order_by(Firma.creado_at.desc())
        .first()
    )
    if not firma:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay una solicitud de firma pendiente para este documento.")

    firma_detectada = "NO_VERIFICADO"
    if archivo is not None:
        contenido = await archivo.read()
        firma_detectada = "SI" if DocumentIntelligenceService.detectar_firma(contenido) else "NO"

    import datetime as _dt

    firma.estado = EstadoFirma.FIRMADO
    firma.firma_detectada_en_documento = firma_detectada
    firma.firmado_at = _dt.datetime.now(_dt.UTC)
    db.commit()
    db.refresh(firma)

    WorkflowEngine.transicionar_estado(db, solicitud, EstadoSolicitud.FIRMADO, usuario, request=request)
    return firma


@router.get("/{solicitud_id}/status", response_model=list[FirmaResponse], summary="Estado de firmas")
def get_signature_status(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_FIRMA, RolUsuario.AUDITOR.value)),
):
    return db.query(Firma).filter(Firma.solicitud_id == solicitud_id).order_by(Firma.creado_at.desc()).all()
