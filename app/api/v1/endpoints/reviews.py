"""Módulo de Comentarios Colaborativos (tabla `comentarios`) y Revisión (tabla `revicion`).

Cubre HU-05 (revisar documentos), HU-06 (agregar comentario) y HU-07
(consultar comentarios).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.audit_helper import registrar_auditoria
from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.comment import Comentario
from app.models.document import Documento
from app.models.revision import DecisionRevision, EstadoRevision, Revision
from app.models.solicitud import EstadoSolicitud, SolicitudRevision
from app.models.user import RolUsuario
from app.models.version import VersionDocumento
from app.schemas.comment import ComentarioCreate, ComentarioResponse
from app.schemas.revision import RevisionCreate, RevisionResponse
from app.services.workflow_engine import WorkflowEngine

router = APIRouter()

ROLES_COMENTARIOS = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
)


@router.get("/{solicitud_id}/comments", response_model=list[ComentarioResponse], summary="Obtener comentarios de una solicitud")
def get_comments(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_COMENTARIOS)),
):
    """HU-07: consulta de comentarios u observaciones (Pantalla 7)."""
    return db.query(Comentario).filter(Comentario.solicitud_id == solicitud_id).order_by(Comentario.creado_at.asc()).all()


@router.post(
    "/{solicitud_id}/comments",
    response_model=ComentarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar comentario u observación",
)
def add_comment(
    solicitud_id: uuid.UUID,
    payload: ComentarioCreate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_COMENTARIOS)),
    request: Request = None,
):
    """HU-06: registro de observación o comentario de revisión, con soporte de hilos de respuesta."""
    solicitud = db.query(SolicitudRevision).get(solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")

    comentario = Comentario(
        solicitud_id=solicitud_id,
        vercion_documento_id=payload.vercion_documento_id,
        user_id=usuario["id"],
        comentario_padre_id=payload.comentario_padre_id,
        contenido=payload.contenido,
    )
    db.add(comentario)
    db.commit()
    db.refresh(comentario)

    registrar_auditoria(
        db,
        usuario,
        accion="Agregó un comentario a la solicitud.",
        tipo_documento="comentario",
        id_documento=comentario.id,
        solicitud_id=solicitud_id,
        request=request,
    )
    return comentario


@router.get(
    "/{solicitud_id}/revision",
    response_model=list[RevisionResponse],
    summary="Listar las revisiones registradas de una solicitud",
    dependencies=[Depends(requiere_roles(*ROLES_COMENTARIOS))],
)
def listar_revisiones(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Obtiene el historial de dictámenes y revisiones registradas para la solicitud."""
    solicitud = db.get(SolicitudRevision, solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")
    return (
        db.query(Revision)
        .filter(Revision.solicitud_id == solicitud_id)
        .order_by(Revision.empezado_at.asc())
        .all()
    )


@router.post(
    "/{solicitud_id}/revision",
    response_model=RevisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar el resultado de una revisión jurídica",
)
def registrar_revision(
    solicitud_id: uuid.UUID,
    payload: RevisionCreate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(RolUsuario.REVISOR_JURIDICO.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value)),
    request: Request = None,
):
    """HU-05 (Pantalla 6, Revisión jurídica): guarda el dictamen del revisor sobre una versión
    y ejecuta la transición de estado correspondiente en las reglas de negocio del workflow.
    """
    solicitud = db.get(SolicitudRevision, solicitud_id)
    if not solicitud:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")


    # Resolución robusta de la versión de documento para evitar violación de FK en la BD
    target_version_id = payload.vercion_documento_id

    if target_version_id:
        v_check = db.query(VersionDocumento).filter(VersionDocumento.id == target_version_id).first()
        if not v_check:
            # Si el frontend envió el ID de un Documento en lugar de la VersionDocumento
            doc_check = db.query(Documento).filter(Documento.id == target_version_id).first()
            if doc_check:
                ult_v = (
                    db.query(VersionDocumento)
                    .filter(VersionDocumento.documento_id == doc_check.id)
                    .order_by(VersionDocumento.numero_version.desc())
                    .first()
                )
                if ult_v:
                    target_version_id = ult_v.id
                else:
                    target_version_id = None
            else:
                target_version_id = None

    if not target_version_id and payload.documento_id:
        doc_check = db.query(Documento).filter(Documento.id == payload.documento_id).first()
        if doc_check:
            ult_v = (
                db.query(VersionDocumento)
                .filter(VersionDocumento.documento_id == doc_check.id)
                .order_by(VersionDocumento.numero_version.desc())
                .first()
            )
            if ult_v:
                target_version_id = ult_v.id

    if not target_version_id:
        # Buscar el primer documento de esta solicitud
        doc_existente = db.query(Documento).filter(Documento.solicitud_id == solicitud_id).first()
        if doc_existente:
            ult_v = (
                db.query(VersionDocumento)
                .filter(VersionDocumento.documento_id == doc_existente.id)
                .order_by(VersionDocumento.numero_version.desc())
                .first()
            )
            if ult_v:
                target_version_id = ult_v.id
            else:
                # Crear versión inicial 1 para asegurar consistencia referencial
                nueva_v = VersionDocumento(
                    documento_id=doc_existente.id,
                    numero_version=1,
                    nombre_archivo=doc_existente.nombre,
                    ubicacion=f"local/{doc_existente.nombre}",
                    tamano_archivo=0,
                    formato_archivo="application/pdf",
                    actualizado_por=usuario["id"],
                )
                db.add(nueva_v)
                db.flush()
                target_version_id = nueva_v.id
        else:
            # Crear documento y versión base en caso de solicitud sin archivos adjuntos
            nuevo_doc = Documento(
                solicitud_id=solicitud_id,
                nombre=f"Instrumento-{solicitud.titulo}",
                tipo_documento=solicitud.tipo_documento or "contrato",
                creado_por=usuario["id"],
            )
            db.add(nuevo_doc)
            db.flush()
            nueva_v = VersionDocumento(
                documento_id=nuevo_doc.id,
                numero_version=1,
                nombre_archivo=nuevo_doc.nombre,
                ubicacion=f"local/{nuevo_doc.nombre}",
                tamano_archivo=0,
                formato_archivo="application/pdf",
                actualizado_por=usuario["id"],
            )
            db.add(nueva_v)
            db.flush()
            target_version_id = nueva_v.id

    import datetime as _dt

    revision = Revision(
        solicitud_id=solicitud_id,
        revizado_id=usuario["id"],
        vercion_documento_id=target_version_id,
        estado=EstadoRevision.COMPLETADA,
        decision=payload.decision,
        notas=payload.notas,
        completado_at=_dt.datetime.now(_dt.UTC),
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)

    # Reglas de transición de Workflow BPM según el dictamen emitido
    if payload.decision == DecisionRevision.APROBAR:
        WorkflowEngine.transicionar_estado(
            db, solicitud, EstadoSolicitud.EN_APROBACION, usuario, motivo=payload.notas, request=request
        )
    elif payload.decision == DecisionRevision.SOLICITAR_CAMBIOS:
        WorkflowEngine.transicionar_estado(
            db, solicitud, EstadoSolicitud.OBSERVADO, usuario, motivo=payload.notas, request=request
        )
    elif payload.decision == DecisionRevision.RECHAZAR:
        WorkflowEngine.transicionar_estado(
            db, solicitud, EstadoSolicitud.RECHAZADO, usuario, motivo=payload.notas, request=request
        )

    registrar_auditoria(
        db,
        usuario,
        accion=f"Registró dictamen de revisión con decisión {payload.decision.value}.",
        tipo_documento="revision",
        id_documento=revision.id,
        solicitud_id=solicitud_id,
        request=request,
    )
    return revision

