"""Servicio de Integración con Azure AI Document Intelligence (OCR + firmas).

Reemplaza el cascarón original (que devolvía `pending_implementation`) con una
implementación real usando el modelo `prebuilt-layout`, que además de extraer
texto y tablas puede reportar si el documento contiene campos de firma.
"""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentIntelligenceService:
    """Extracción de texto/cláusulas y detección de firmas en PDFs y contratos."""

    _client: Any = None

    @classmethod
    def get_client(cls) -> Any:
        """Inicializa el cliente de Document Intelligence con soporte híbrido:
        1. API Key si está configurada (entorno local).
        2. Managed Identity (DefaultAzureCredential) en Azure (Passwordless).
        """
        if not settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT:
            logger.warning("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT no está configurado.")
            return None

        if cls._client is None:
            try:
                from azure.ai.documentintelligence import DocumentIntelligenceClient
            except ImportError:
                logger.warning("Librería azure-ai-documentintelligence no instalada en este entorno.")
                return None

            doc_intel_key = settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
            if doc_intel_key:
                from azure.core.credentials import AzureKeyCredential

                cls._client = DocumentIntelligenceClient(
                    endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
                    credential=AzureKeyCredential(doc_intel_key),
                )
            else:
                try:
                    from azure.identity import DefaultAzureCredential

                    cls._client = DocumentIntelligenceClient(
                        endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
                        credential=DefaultAzureCredential(),
                    )
                except Exception as e:
                    logger.error("Error al inicializar Document Intelligence con Managed Identity: %s", e, exc_info=True)
                    return None
        return cls._client

    @classmethod
    def extract_clauses_from_pdf(cls, pdf_bytes: bytes) -> dict:
        """Extrae el texto plano, tablas y cláusulas de un PDF o imagen usando el modelo `prebuilt-layout`.

        El texto resultante en Markdown se usa después para: (a) el análisis de riesgos con
        IA (azure_openai.py::analyze_legal_risks) y (b) la clasificación
        automática de área (azure_openai.py::clasificar_area).
        """
        client = cls.get_client()
        if not client:
            return {"status": "pending_implementation", "texto": "", "clauses": []}

        import io

        try:
            poller = client.begin_analyze_document(
                "prebuilt-layout",
                body=io.BytesIO(pdf_bytes),
                output_content_format="markdown",
            )
            resultado = poller.result()
            texto_completo = resultado.content or ""
            return {
                "status": "ok",
                "texto": texto_completo,
                "clauses": [p.content for p in getattr(resultado, "paragraphs", []) or []],
            }
        except Exception:
            try:
                poller = client.begin_analyze_document("prebuilt-layout", body=io.BytesIO(pdf_bytes))
                resultado = poller.result()
                texto_completo = resultado.content or ""
                return {
                    "status": "ok",
                    "texto": texto_completo,
                    "clauses": [p.content for p in getattr(resultado, "paragraphs", []) or []],
                }
            except Exception as e:
                logger.error("Error al extraer texto con Document Intelligence: %s", e, exc_info=True)
                return {"status": "error", "texto": "", "clauses": []}

    @classmethod
    def detectar_firma(cls, pdf_bytes: bytes) -> bool:
        """Indica si el PDF ya contiene una firma manuscrita/sello detectable."""
        client = cls.get_client()
        if not client:
            return False

        import io

        try:
            poller = client.begin_analyze_document("prebuilt-document", body=io.BytesIO(pdf_bytes))
            resultado = poller.result()
            firmas = getattr(resultado, "signatures", None) or []
            return len(firmas) > 0
        except Exception as e:
            logger.warning("Detección de firmas no disponible en el recurso o modelo configurado: %s", e)
            return False
