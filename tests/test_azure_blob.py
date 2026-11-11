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


def test_respaldo_local_cadena_azure_invalida(tmp_path, monkeypatch):
    """Verifica que con una cadena de conexión de Azure inválida/corrupta, upload_file guarde en local sin tronar."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "AZURE_STORAGE_CONNECTION_STRING", "# ← Pegar aquí la Connection string completa", raising=False)
    monkeypatch.setattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None, raising=False)
    AzureBlobService._client = None

    ubicacion = AzureBlobService.upload_file("2-v1-acuerdo.pdf", b"%PDF-acuerdo-contenido-local")

    assert AzureBlobService.download_file(ubicacion) == b"%PDF-acuerdo-contenido-local"


def test_generate_sas_url_sin_credenciales(monkeypatch):
    """Verifica que sin cliente con account_key, generate_sas_url retorne None sin tronar."""
    monkeypatch.setattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None, raising=False)
    monkeypatch.setattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None, raising=False)
    AzureBlobService._client = None

    sas = AzureBlobService.generate_sas_url("test-blob.pdf")
    assert sas is None


def test_download_file_limpieza_querystring(tmp_path, monkeypatch):
    """Verifica que download_file limpie querystrings al buscar blobs locales o en Azure."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None, raising=False)
    monkeypatch.setattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None, raising=False)
    AzureBlobService._client = None

    ubicacion = AzureBlobService.upload_file("test-qs.pdf", b"%PDF-qs-test")
    url_con_qs = f"{ubicacion}?sig=fake123&se=2026-12-31"

    assert AzureBlobService.download_file(url_con_qs) == b"%PDF-qs-test"


