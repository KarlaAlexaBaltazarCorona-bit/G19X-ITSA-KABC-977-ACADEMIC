"""Módulo de Bandeja de Trabajo (HU-02, HU-04) -- opera sobre `solicitud_r`.

Ya NO existe una tabla `tareas_workflow` separada: la "bandeja de trabajo" de
un Revisor/Aprobador es, simplemente, las filas de `solicitud_r` donde
`revicion_id` es su propio usuario y el `estado` sigue activo.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.solicitud import EstadoSolicitud, SolicitudRevision
from app.models.user import RolUsuario
from app.schemas.solicitud import SolicitudResponse

router = APIRouter()

ESTADOS_ACTIVOS = (EstadoSolicitud.EN_REVISION, EstadoSolicitud.OBSERVADO, EstadoSolicitud.EN_APROBACION)


@router.get("/inbox", response_model=list[SolicitudResponse], summary="Bandeja de trabajo del usuario")
def get_work_inbox(
    db: Session = Depends(get_db),
    usuario: dict = Depends(
        requiere_roles(RolUsuario.REVISOR_JURIDICO.value, RolUsuario.APROBADOR_JURIDICO.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value)
    ),
):
    """Consulta las solicitudes asignadas y activas del usuario autenticado (Pantalla 3).

    El `ADMINISTRADOR_PLATAFORMA` ve TODAS las solicitudes activas (para poder
    reasignar); los demás roles solo ven las suyas.
    """
    query = db.query(SolicitudRevision).filter(SolicitudRevision.estado.in_(ESTADOS_ACTIVOS))
    if usuario["rol"] != RolUsuario.ADMINISTRADOR_PLATAFORMA.value:
        query = query.filter(SolicitudRevision.revicion_id == usuario["id"])
    return query.order_by(SolicitudRevision.fecha_limite.asc().nullslast()).all()
