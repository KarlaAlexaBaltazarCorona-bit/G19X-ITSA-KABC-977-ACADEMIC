"""Servicio de Integración con Azure Blob Storage para Repositorio Documental."""

import logging
import os
from pathlib import Path
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
                try:
                    cls._client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
                except Exception as e:
                    logger.error("Cadena de conexión de Blob inválida: %s", e)
                    return None
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
        container_name = settings.AZURE_STORAGE_CONTAINER_NAME or "documentos"
        blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{filename}"

        # Guardar copia local en caché para descargas instantáneas en entornos locales o baja latencia
        local_dir = Path("local_storage") / container_name
        local_dir.mkdir(parents=True, exist_ok=True)
        try:
            (local_dir / Path(filename).name).write_bytes(content)
        except Exception as e_local:
            logger.warning("No se pudo escribir copia local en caché: %s", e_local)

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
    def generate_sas_url(cls, filename_or_url: str, expiry_hours: int = 2) -> str | None:
        """Genera una URL temporal con SAS Token (lectura) para descarga segura desde el navegador."""
        if not filename_or_url:
            return None
        container_name = settings.AZURE_STORAGE_CONTAINER_NAME or "documentos"
        blob_name = filename_or_url
        if f"/{container_name}/" in filename_or_url:
            blob_name = filename_or_url.split(f"/{container_name}/", 1)[-1]
        elif "/" in filename_or_url and not (filename_or_url.startswith("http://") or filename_or_url.startswith("https://")):
            blob_name = filename_or_url.split("/")[-1]

        # Quitar parámetros previos si ya tuviera querystring
        blob_name = blob_name.split("?")[0]

        client = cls.get_client()
        if client and hasattr(client, "credential") and hasattr(client.credential, "account_key") and client.credential.account_key:
            try:
                from datetime import UTC, datetime, timedelta
                from azure.storage.blob import BlobSasPermissions, generate_blob_sas

                account_name = getattr(client, "account_name", None) or settings.AZURE_STORAGE_ACCOUNT_NAME
                sas = generate_blob_sas(
                    account_name=account_name,
                    container_name=container_name,
                    blob_name=blob_name,
                    account_key=client.credential.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.now(UTC) + timedelta(hours=expiry_hours),
                )
                return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas}"
            except Exception as e:
                logger.warning("No se pudo generar SAS URL para '%s': %s", blob_name, e)

        return None

    @classmethod
    def download_file(cls, filename_or_url: str) -> bytes | None:
        """Descarga el contenido binario de un archivo desde Azure Blob Storage o caché local."""
        if not filename_or_url:
            return None

        container_name = settings.AZURE_STORAGE_CONTAINER_NAME or "documentos"

        # Extraer nombre del blob si se pasó una URL completa
        blob_name = filename_or_url
        if f"/{container_name}/" in filename_or_url:
            blob_name = filename_or_url.split(f"/{container_name}/", 1)[-1]
        elif "/" in filename_or_url and not (filename_or_url.startswith("http://") or filename_or_url.startswith("https://")):
            blob_name = filename_or_url.split("/")[-1]

        # Quitar parámetros query (?...) si los tuviera
        blob_name = blob_name.split("?")[0]

        # 1. Respaldo / Caché local primero (máxima velocidad, 0 latencia de red)
        local_dir = Path("local_storage") / container_name
        local_copy = local_dir / Path(blob_name).name
        if local_copy.is_file():
            try:
                return local_copy.read_bytes()
            except Exception as e_read:
                logger.warning("Fallo al leer caché local '%s': %s", local_copy, e_read)

        if os.path.exists(filename_or_url):
            try:
                with open(filename_or_url, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.warning("Fallo al leer archivo local '%s': %s", filename_or_url, e)

        # 2. Descargar de Azure Blob Storage oficial
        client = cls.get_client()
        if client:
            try:
                blob_client = client.get_blob_client(container=container_name, blob=blob_name)
                download_stream = blob_client.download_blob()
                data = download_stream.readall()
                # Guardar en caché local para próximas peticiones inmediatas
                try:
                    local_dir.mkdir(parents=True, exist_ok=True)
                    local_copy.write_bytes(data)
                except Exception:
                    pass
                return data
            except Exception as e:
                logger.warning("Fallo al descargar blob '%s' vía BlobClient: %s", blob_name, e)

        # 3. Si es URL HTTP/HTTPS y el cliente directo no funcionó, intentar vía HTTP request
        if filename_or_url.startswith("http://") or filename_or_url.startswith("https://"):
            try:
                import requests
                resp = requests.get(filename_or_url, timeout=15)
                if resp.status_code == 200:
                    try:
                        local_dir.mkdir(parents=True, exist_ok=True)
                        local_copy.write_bytes(resp.content)
                    except Exception:
                        pass
                    return resp.content
            except Exception as e:
                logger.warning("Fallo al descargar blob vía HTTP desde '%s': %s", filename_or_url, e)

        return None

