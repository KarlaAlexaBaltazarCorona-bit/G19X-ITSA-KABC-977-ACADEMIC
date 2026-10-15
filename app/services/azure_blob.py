"""Servicio de Integración con Azure Blob Storage para Repositorio Documental."""

import logging
from typing import Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class AzureBlobService:
    """Manejo de subida, descarga y versionado de contratos en Azure Blob Storage."""

    _client: Any = None

    @classmethod
    def get_client(cls) -> Any:
        """Inicializa el cliente de Blob Storage con soporte híbrido:
        1. Connection String si está configurada (entorno local).
        2. Managed Identity (DefaultAzureCredential) en Azure (Passwordless).
        """
        if cls._client is None:
            try:
                from azure.storage.blob import BlobServiceClient
            except ImportError:
                logger.warning("Librería azure-storage-blob no instalada en este entorno.")
                return None
            if settings.AZURE_STORAGE_CONNECTION_STRING:
                logger.info("Inicializando Azure Blob Storage mediante Connection String.")
                cls._client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
            elif settings.AZURE_STORAGE_ACCOUNT_NAME:
                logger.info("Inicializando Azure Blob Storage mediante Managed Identity (DefaultAzureCredential).")
                try:
                    from azure.identity import DefaultAzureCredential

                    account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
                    cls._client = BlobServiceClient(
                        account_url=account_url,
                        credential=DefaultAzureCredential(),
                    )
                except Exception as e:
                    logger.error("Error al inicializar Blob Storage con Managed Identity: %s", e, exc_info=True)
                    return None
        return cls._client

    @classmethod
    def upload_file(cls, filename: str, content: bytes) -> str:
        """Sube un archivo al contenedor de documentos legales y retorna su URL canónica."""
        account_name = settings.AZURE_STORAGE_ACCOUNT_NAME or "almacenlegalprojectia"
        container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{filename}"

        client = cls.get_client()
        if client:
            try:
                blob_client = client.get_blob_client(container=container_name, blob=filename)
                blob_client.upload_blob(content, overwrite=True)
                return blob_url
            except Exception as e:
                logger.error("Error al subir blob a Azure Storage: %s", e, exc_info=True)

        return blob_url

    @classmethod
    def download_file(cls, filename_or_url: str) -> bytes | None:
        """Descarga el contenido binario de un archivo desde Azure Blob Storage."""
        if not filename_or_url:
            return None

        container_name = settings.AZURE_STORAGE_CONTAINER_NAME or "documentos"

        # Extraer nombre del blob si se pasó una URL completa
        blob_name = filename_or_url
        if f"/{container_name}/" in filename_or_url:
            blob_name = filename_or_url.split(f"/{container_name}/", 1)[-1]
        elif "/" in filename_or_url and not (filename_or_url.startswith("http://") or filename_or_url.startswith("https://")):
            blob_name = filename_or_url.split("/")[-1]

        # 1. Intentar descargar usando el cliente oficial de Azure Blob
        client = cls.get_client()
        if client:
            try:
                blob_client = client.get_blob_client(container=container_name, blob=blob_name)
                download_stream = blob_client.download_blob()
                return download_stream.readall()
            except Exception as e:
                logger.warning("Fallo al descargar blob '%s' vía BlobClient: %s", blob_name, e)

        # 2. Si es URL HTTP/HTTPS y el cliente directo no funcionó, intentar vía HTTP request
        if filename_or_url.startswith("http://") or filename_or_url.startswith("https://"):
            try:
                import requests
                resp = requests.get(filename_or_url, timeout=10)
                if resp.status_code == 200:
                    return resp.content
            except Exception as e:
                logger.warning("Fallo al descargar blob vía HTTP desde '%s': %s", filename_or_url, e)

        # 3. Fallback: verificar si es una ruta local existente (pruebas o entorno local)
        import os
        if os.path.exists(filename_or_url):
            try:
                with open(filename_or_url, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.warning("Fallo al leer archivo local '%s': %s", filename_or_url, e)

        return None

