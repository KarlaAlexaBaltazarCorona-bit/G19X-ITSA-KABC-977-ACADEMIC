"""Servicio de Integración con Azure AI Search (Búsqueda Vectorial y Semántica)."""

import logging
from typing import Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class AzureSearchService:
    """Indexación y búsqueda de antecedentes, jurisprudencia interna y contratos similares."""

    _client: Any = None

    @classmethod
    def get_client(cls, index_name: str = "contratos-index") -> Any:
        """Inicializa cliente de Azure AI Search con soporte híbrido:
        1. API Key si está configurada (entorno local).
        2. Managed Identity (DefaultAzureCredential) en Azure (Passwordless).
        """
        if not settings.AZURE_SEARCH_ENDPOINT:
            return None

        if cls._client is None:
            try:
                from azure.search.documents import SearchClient
            except ImportError:
                logger.warning("Librería azure-search-documents no instalada en este entorno.")
                return None
            if settings.AZURE_SEARCH_KEY:
                logger.info("Inicializando Azure AI Search mediante API Key.")
                from azure.core.credentials import AzureKeyCredential

                cls._client = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=index_name,
                    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY),
                )
            else:
                logger.info("Inicializando Azure AI Search mediante Managed Identity (DefaultAzureCredential).")
                try:
                    from azure.identity import DefaultAzureCredential

                    cls._client = SearchClient(
                        endpoint=settings.AZURE_SEARCH_ENDPOINT,
                        index_name=index_name,
                        credential=DefaultAzureCredential(),
                    )
                except Exception as e:
                    logger.error("Error al inicializar Azure AI Search con Managed Identity: %s", e, exc_info=True)
                    return None
        return cls._client

    @classmethod
    def search_similar_documents(cls, query_vector_or_text: str) -> list[dict[str, Any]]:
        """Consulta el índice semántico de Azure AI Search."""
        client = cls.get_client()
        if not client:
            return []
        try:
            results = client.search(search_text=query_vector_or_text, top=5)
            return [dict(doc) for doc in results]
        except Exception as e:
            logger.error("Error en búsqueda semántica de Azure Search: %s", e, exc_info=True)
            return []
