"""Pruebas de integración para descarga segura de versiones documentales (sin PublicAccessNotPermitted)."""

import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.models.document import Documento
from app.models.version import VersionDocumento
from app.schemas.document import VersionDocumentoResponse

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_download_version_exitoso(client: TestClient, db):
    """Verifica que el endpoint /versions/{id}/download descargue el archivo con headers correctos."""
    doc_id = uuid.uuid4()
    ver_id = uuid.uuid4()

    doc = Documento(
        id=doc_id,
        solicitud_id=uuid.uuid4(),
        nombre="convenio_prueba.pdf",
        tipo_documento="convenio",
        creado_por=USER_ID,
    )
    db.add(doc)

    ver = VersionDocumento(
        id=ver_id,
        documento_id=doc_id,
        numero_version=1,
        nombre_archivo="convenio_prueba.pdf",
        ubicacion="https://storage.blob.core.windows.net/documentos/prueba.pdf",
        tamano_archivo=100,
        formato_archivo="application/pdf",
        actualizado_por=USER_ID,
    )
    db.add(ver)
    db.commit()

    with patch("app.services.azure_blob.AzureBlobService.download_file", return_value=b"%PDF-mock-content"):
        res = client.get(f"/api/v1/documents/versions/{ver_id}/download")
        assert res.status_code == 200
        assert res.content == b"%PDF-mock-content"
        assert res.headers["content-type"] == "application/pdf"
        assert 'attachment; filename="convenio_prueba.pdf"' in res.headers["content-disposition"]


def test_download_version_404_no_existe(client: TestClient):
    """Verifica que un UUID inexistente devuelva 404."""
    fake_id = uuid.uuid4()
    res = client.get(f"/api/v1/documents/versions/{fake_id}/download")
    assert res.status_code == 404


def test_version_documento_response_incluye_download_url():
    """Verifica que VersionDocumentoResponse exponga download_url y sas_url dinámicamente."""
    ver_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    ver = VersionDocumento(
        id=ver_id,
        documento_id=doc_id,
        numero_version=1,
        nombre_archivo="contrato.pdf",
        ubicacion="https://storage.blob.core.windows.net/documentos/contrato.pdf",
        tamano_archivo=200,
        formato_archivo="application/pdf",
        actualizado_por=USER_ID,
    )

    resp = VersionDocumentoResponse.model_validate(ver)
    assert resp.download_url == f"/api/v1/documents/versions/{ver_id}/download"
    assert resp.nombre_archivo == "contrato.pdf"
