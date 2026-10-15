"""Módulo de Búsqueda Semántica y Vectorial (Azure AI Search)."""

from fastapi import APIRouter, Depends

from app.core.roles_guard import requiere_roles
from app.models.user import RolUsuario
from app.services.azure_search import AzureSearchService

router = APIRouter()

ROLES_TODOS = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.AUDITOR.value,
)


@router.get(
    "/semantic",
    summary="Búsqueda semántica de solicitudes/documentos",
    dependencies=[Depends(requiere_roles(*ROLES_TODOS))],
)
def semantic_search(query: str):
    """Búsqueda de precedentes y documentos similares usando Azure AI Search."""
    resultados = AzureSearchService.search_similar_documents(query)
    return {"query": query, "results": resultados}


@router.post(
    "/index-document",
    summary="Indexar documento en Azure Search",
    dependencies=[Depends(requiere_roles(RolUsuario.ADMINISTRADOR_PLATAFORMA.value))],
)
def index_document():
    """Cascarón: la indexación real se dispara automáticamente al guardar una versión
    (ver app/services/workflow_engine.py) una vez que el índice de Azure Search esté
    definido con sus campos -- esta ruta queda disponible para reindexar manualmente."""
    return {"status": "pending_implementation"}
