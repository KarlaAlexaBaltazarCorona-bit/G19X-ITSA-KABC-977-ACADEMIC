"""Módulo de Documentos (tabla `documento`) y sus Versiones (tabla `vercion_documento`).

Cubre HU-08 (control de versiones) y HU-09 (consultar versiones). La carga
del PRIMER documento de una solicitud ocurre en `solicitudes.py::create_solicitud`;
este módulo maneja documentos adicionales y nuevas versiones de uno ya existente.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.document import Documento
from app.models.solicitud import EstadoSolicitud, SolicitudRevision
from app.models.user import RolUsuario
from app.models.version import VersionDocumento
from app.schemas.document import DocumentResponse, VersionDocumentoResponse
from app.services.azure_blob import AzureBlobService
from app.services.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)


router = APIRouter()

ROLES_TODOS = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.AUDITOR.value,
)

ROLES_MODIFICACION = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
)


@router.get("/{solicitud_id}", response_model=list[DocumentResponse], summary="Listar documentos de una solicitud")
def list_documents(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """Consulta los documentos (archivos) cargados dentro de una Solicitud_R."""
    solicitud = db.query(SolicitudRevision).get(solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")
    return db.query(Documento).filter(Documento.solicitud_id == solicitud_id).all()


@router.post(
    "/{solicitud_id}/documentos",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un documento adicional a una solicitud ya existente",
)
async def add_document(
    solicitud_id: uuid.UUID,
    nombre: str,
    tipo_documento: str,
    archivo: UploadFile,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_MODIFICACION)),
    request: Request = None,
):
    """Para cuando una solicitud necesita más de un archivo adjunto."""
    solicitud = db.query(SolicitudRevision).get(solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")
    if solicitud.estado in (EstadoSolicitud.RECHAZADO, EstadoSolicitud.FIRMADO):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No se pueden agregar documentos a una solicitud en estado terminal ({solicitud.estado.value}).",
        )

    documento = Documento(solicitud_id=solicitud_id, nombre=nombre, tipo_documento=tipo_documento, creado_por=usuario["id"])
    db.add(documento)
    db.commit()
    db.refresh(documento)

    contenido = await archivo.read()
    ver = WorkflowEngine.guardar_version_si_cambio(
        db,
        documento,
        contenido=contenido,
        nombre_archivo=archivo.filename or nombre,
        formato_archivo=(archivo.content_type or "application/octet-stream"),
        usuario=usuario,
        request=request,
    )
    try:
        from app.services.document_extractor import cache_document_text, extract_text_from_bytes
        txt = extract_text_from_bytes(contenido, archivo.filename or nombre, archivo.content_type or "")
        if txt:
            cache_document_text(documento.id, txt)
            cache_document_text(solicitud_id, txt)
            if ver:
                cache_document_text(ver.id, txt)
    except Exception as e:
        logger.warning("Fallo al pre-cachear texto en documents.py: %s", e)
    return documento


@router.get(
    "/detalle/{documento_id}/versions",
    response_model=list[VersionDocumentoResponse],
    summary="Historial de versiones de un documento",
)
def get_document_versions(
    documento_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """Consulta de versiones anteriores de un documento (HU-08, HU-09, Pantalla 8)."""
    documento = db.query(Documento).get(documento_id)
    if not documento:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")
    return sorted(documento.versiones, key=lambda v: v.numero_version, reverse=True)


@router.post(
    "/detalle/{documento_id}/versions",
    response_model=VersionDocumentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Guardar una nueva versión de un documento existente",
)
async def add_document_version(
    documento_id: uuid.UUID,
    archivo: UploadFile,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_MODIFICACION)),
    request: Request = None,
):
    """Sube una nueva versión. Solo crea una fila nueva si el contenido cambió."""
    documento = db.query(Documento).get(documento_id)
    if not documento:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")

    solicitud = db.query(SolicitudRevision).get(documento.solicitud_id)
    if solicitud and solicitud.estado in (EstadoSolicitud.RECHAZADO, EstadoSolicitud.FIRMADO):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No se pueden subir nuevas versiones a una solicitud en estado terminal ({solicitud.estado.value}).",
        )

    contenido = await archivo.read()
    nueva_version = WorkflowEngine.guardar_version_si_cambio(
        db,
        documento,
        contenido=contenido,
        nombre_archivo=archivo.filename or documento.nombre,
        formato_archivo=(archivo.content_type or "application/octet-stream"),
        usuario=usuario,
        request=request,
    )
    try:
        from app.services.document_extractor import cache_document_text, extract_text_from_bytes
        txt = extract_text_from_bytes(contenido, archivo.filename or documento.nombre, archivo.content_type or "")
        if txt:
            cache_document_text(documento.id, txt)
            cache_document_text(documento.solicitud_id, txt)
            if nueva_version:
                cache_document_text(nueva_version.id, txt)
    except Exception as e:
        logger.warning("Fallo al pre-cachear texto en version upload: %s", e)
    return nueva_version


@router.get(
    "/versions/{version_id}/download",
    summary="Descargar archivo físico de una versión específica",
    description="Permite descargar de forma segura un archivo sin incurrir en errores de PublicAccessNotPermitted de Azure Blob Storage.",
)
def download_document_version(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """Descarga de forma autenticada el archivo físico asociado a una versión específica."""
    version = db.query(VersionDocumento).filter(VersionDocumento.id == version_id).first()
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión de documento no encontrada.")

    contenido = AzureBlobService.download_file(version.ubicacion)
    if not contenido:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "El archivo digital no se encuentra disponible en el repositorio de almacenamiento.",
        )

    # Determinar Content-Type
    media_type = version.formato_archivo or "application/octet-stream"
    if not media_type or media_type.lower() in ("string", "null", "undefined"):
        nombre_lower = version.nombre_archivo.lower()
        if nombre_lower.endswith(".pdf"):
            media_type = "application/pdf"
        elif nombre_lower.endswith(".docx"):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif nombre_lower.endswith(".doc"):
            media_type = "application/msword"
        else:
            media_type = "application/octet-stream"

    nombre_seguro = version.nombre_archivo.replace('"', '').replace('\n', '').replace('\r', '')

    return Response(
        content=contenido,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_seguro}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get(
    "/detalle/{documento_id}/download",
    summary="Descargar archivo físico de la última versión de un documento",
)
def download_document_latest(
    documento_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """Descarga la versión más reciente de un documento."""
    documento = db.query(Documento).filter(Documento.id == documento_id).first()
    if not documento:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")

    ultima_version = (
        db.query(VersionDocumento)
        .filter(VersionDocumento.documento_id == documento_id)
        .order_by(VersionDocumento.numero_version.desc())
        .first()
    )
    if not ultima_version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El documento no tiene versiones registradas.")

    return download_document_version(version_id=ultima_version.id, db=db, usuario=usuario)


@router.get(
    "/solicitud/{solicitud_id}/download",
    summary="Descargar el documento principal de una solicitud",
)
def download_solicitud_document(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """Descarga el primer documento adjunto de una solicitud."""
    doc = db.query(Documento).filter(Documento.solicitud_id == solicitud_id).first()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La solicitud no contiene documentos adjuntos.")

    return download_document_latest(documento_id=doc.id, db=db, usuario=usuario)

