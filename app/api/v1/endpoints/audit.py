"""Módulo de Trazabilidad y Auditoría (tabla `auditoria`) -- HU-12."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.audit import Auditoria
from app.models.user import RolUsuario
from app.schemas.audit import AuditoriaResponse

router = APIRouter()


ROLES_AUDITORIA = (
    RolUsuario.AUDITOR.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.APROBADOR_JURIDICO.value,
)


@router.get("/trail", response_model=list[AuditoriaResponse], summary="Línea de tiempo global de auditoría")
@router.get("/trail/global", response_model=list[AuditoriaResponse], summary="Línea de tiempo global de auditoría (alias)")
def get_global_audit_trail(
    limit: int = 150,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_AUDITORIA)),
):
    """Retorna los registros de auditoría más recientes con detalles de usuario, timestamps y acciones."""
    return (
        db.query(Auditoria)
        .order_by(Auditoria.creada_at.desc())
        .limit(max(1, min(limit, 500)))
        .all()
    )


@router.get("/trail/{solicitud_id}", response_model=list[AuditoriaResponse], summary="Línea de tiempo de auditoría")
def get_audit_trail(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_AUDITORIA)),
):
    """HU-12 (Pantalla 11, Trazabilidad): toda la bitácora de una solicitud, más reciente primero."""
    return (
        db.query(Auditoria)
        .filter(Auditoria.solicitud_id == solicitud_id)
        .order_by(Auditoria.creada_at.desc())
        .all()
    )
