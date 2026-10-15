"""Agrupador de endpoints para la versión 1 de la API con protección de acceso."""

from fastapi import APIRouter, Depends
from app.core.auth_guard import verify_api_key
from app.core.rate_limiter import rate_limit_guard
from app.api.v1.endpoints import (
    frontend,
    ai_legal,
    audit,
    auth,
    documents,
    notifications,
    organizations,
    reviews,
    search,
    signatures,
    solicitudes,
    workflows,
    analytics,
    users,
)

# Sub-router protegido para todos los módulos de negocio legal
# Bloquea de raíz escaneos y enumeración de Gobuster / Burp Suite (exige X-API-KEY y aplica Rate Limiting)
protected_router = APIRouter(dependencies=[Depends(verify_api_key), Depends(rate_limit_guard)])
protected_router.include_router(organizations.router, prefix="/organizations", tags=["Organizaciones (desactivado)"])
protected_router.include_router(solicitudes.router, prefix="/solicitudes", tags=["Solicitudes de Revisión"])
protected_router.include_router(documents.router, prefix="/documents", tags=["Gestión Documental"])
protected_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows y Bandejas"])
protected_router.include_router(reviews.router, prefix="/reviews", tags=["Revisiones y Comentarios"])
protected_router.include_router(signatures.router, prefix="/signatures", tags=["Firmas Electrónicas"])
protected_router.include_router(ai_legal.router, prefix="/ai", tags=["Inteligencia Artificial Jurídica"])
protected_router.include_router(search.router, prefix="/search", tags=["Búsqueda Semántica"])
protected_router.include_router(audit.router, prefix="/audit", tags=["Auditoría y Trazabilidad"])
protected_router.include_router(analytics.router, prefix="/analytics", tags=["Analítica y Power BI"])
protected_router.include_router(users.router, prefix="/usuarios", tags=["Gestión de Usuarios"])
protected_router.include_router(users.router, prefix="/users", tags=["Gestión de Usuarios (alias)"])
# Páginas HTML del portal interno (pantallas 2–13)
protected_router.include_router(frontend.router, prefix="/app", tags=["Portal HTML"])
protected_router.include_router(notifications.router, prefix="/notifications", tags=["Alertas y Notificaciones"])

api_router = APIRouter()
# El módulo de autenticación maneja sus propias rutas públicas (login, config, me)
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
# Montar los módulos de negocio blindados
api_router.include_router(protected_router)
