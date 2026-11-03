"""Pruebas unitarias para el servicio de Azure Blob y respaldo documental local."""

from app.core.config import settings
from app.services.azure_blob import AzureBlobService


def test_respaldo_local_sin_azure(tmp_path, monkeypatch):
    """Verifica que sin credenciales de Azure, upload_file guarde en local y download_file lo recupere."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None, raising=False)
    monkeypatch.setattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None, raising=False)
    AzureBlobService._client = None

    ubicacion = AzureBlobService.upload_file("1-v1-contrato.pdf", b"%PDF-prueba")

    assert AzureBlobService.download_file(ubicacion) == b"%PDF-prueba"
