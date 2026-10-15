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


@router.get("/trail/{solicitud_id}", response_model=list[AuditoriaResponse], summary="Línea de tiempo de auditoría")
def get_audit_trail(
    solicitud_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(
        requiere_roles(RolUsuario.AUDITOR.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value, RolUsuario.APROBADOR_JURIDICO.value)
    ),
):
    """HU-12 (Pantalla 11, Trazabilidad): toda la bitácora de una solicitud, más reciente primero."""
    return (
        db.query(Auditoria)
        .filter(Auditoria.solicitud_id == solicitud_id)
        .order_by(Auditoria.creada_at.desc())
        .all()
    )
