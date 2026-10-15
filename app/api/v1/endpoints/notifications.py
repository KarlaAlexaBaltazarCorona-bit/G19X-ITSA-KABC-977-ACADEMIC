"""Módulo de Alertas y Notificaciones (tabla extra `notificaciones`) -- HU-13."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.extras import Notificacion
from app.models.user import RolUsuario
from app.schemas.audit import NotificacionResponse

router = APIRouter()

ROLES_TODOS = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.AUDITOR.value,
)


@router.get("/pending", response_model=list[NotificacionResponse], summary="Notificaciones pendientes del usuario")
def get_pending_notifications(
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """HU-13: alertas activas del usuario autenticado (asignaciones, vencimientos, comentarios nuevos)."""
    return (
        db.query(Notificacion)
        .filter(Notificacion.user_id == usuario["id"], Notificacion.leida == False)  # noqa: E712
        .order_by(Notificacion.creado_at.desc())
        .all()
    )


@router.post("/{notificacion_id}/leer", response_model=NotificacionResponse, summary="Marcar notificación como leída")
def marcar_leida(
    notificacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    notificacion = db.query(Notificacion).get(notificacion_id)
    if not notificacion or str(notificacion.user_id) != usuario["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificación no encontrada.")
    notificacion.leida = True
    db.commit()
    db.refresh(notificacion)
    return notificacion
