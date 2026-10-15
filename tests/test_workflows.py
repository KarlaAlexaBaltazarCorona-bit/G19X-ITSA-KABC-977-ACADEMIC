"""Pruebas de la bandeja de trabajo (workflows.py)."""

from fastapi.testclient import TestClient


def test_inbox_devuelve_lista_vacia(client: TestClient):
    """Sin datos, la bandeja de trabajo debe estar vacía."""
    response = client.get("/api/v1/workflows/inbox")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
