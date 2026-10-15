from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.tenant import TenantModel
from app.models.user import RolUsuario

router = APIRouter()


@router.get("/", summary="Listar organizaciones y tenants registrados en el sistema")
def list_organizations(
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(RolUsuario.ADMINISTRADOR_PLATAFORMA.value, RolUsuario.AUDITOR.value)),
):
    """Consulta las organizaciones/inquilinos corporativos registrados en el catálogo del sistema."""
    tenants = db.query(TenantModel).order_by(TenantModel.nombre_comercial.asc()).all()
    return {
        "items": [
            {
                "id": str(t.id),
                "nombre_comercial": t.nombre_comercial,
                "rfc": t.rfc,
                "activo": t.activo,
            }
            for t in tenants
        ],
        "total": len(tenants),
    }
