"""Pruebas unitarias, de integración y de seguridad para el módulo de IA Jurídica."""

import os
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from main import app
from app.core.config import settings
from app.services.azure_openai import LegalAIService

client = TestClient(app)


def get_auth_headers() -> dict[str, str]:
    """Retorna los encabezados con la API Key configurada para pruebas."""
    if settings.APP_API_KEY:
        return {"X-API-KEY": settings.APP_API_KEY}
    return {}


def test_ai_query_endpoint_with_mock():
    """Verifica el flujo del endpoint /api/v1/ai/query usando un mock (garantiza éxito en CI)."""
    mock_result = {
        "respuesta": "Las 2 partes principales son el arrendador y el arrendatario.",
        "modelo": "gpt-5-mini",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
    with patch.object(LegalAIService, "ask_legal_assistant", return_value=mock_result):
        payload = {
            "prompt": "¿Cuáles son las partes de un contrato de arrendamiento?",
            "contexto": "Inmuebles comerciales",
        }
        response = client.post("/api/v1/ai/query", json=payload, headers=get_auth_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["respuesta"] == mock_result["respuesta"]
        assert data["modelo"] == "gpt-5-mini"


def test_ai_risk_analysis_endpoint_with_mock():
    """Verifica el endpoint /api/v1/ai/risk-analysis con mock."""
    mock_result = {
        "analisis_detallado": "1. RIESGO MEDIO: Se detecta falta de cláusula de arbitraje.",
        "modelo": "gpt-5-mini",
        "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
    }
    with patch.object(LegalAIService, "analyze_legal_risks", return_value=mock_result):
        payload = {
            "contract_text": "Cláusula Primera: El proveedor se compromete al desarrollo de software...",
            "tipo_documento": "contrato",
        }
        response = client.post("/api/v1/ai/risk-analysis", json=payload, headers=get_auth_headers())
        assert response.status_code == 200
        assert "RIESGO MEDIO" in response.json()["analisis_detallado"]


def test_ai_summarize_endpoint_with_mock():
    """Verifica el endpoint /api/v1/ai/summarize con mock."""
    mock_result = {
        "resumen_ejecutivo": "Contrato de servicios celebrado entre Parte A y Parte B.",
        "modelo": "gpt-5-mini",
        "usage": {"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50},
    }
    with patch.object(LegalAIService, "summarize_contract", return_value=mock_result):
        payload = {
            "contract_text": "Texto del acuerdo de confidencialidad de 2 años...",
        }
        response = client.post("/api/v1/ai/summarize", json=payload, headers=get_auth_headers())
        assert response.status_code == 200
        assert "Parte A y Parte B" in response.json()["resumen_ejecutivo"]


def test_ai_endpoint_rejects_missing_api_key():
    """Verifica que un intento sin X-API-KEY sea rechazado con 401 si hay APP_API_KEY configurada."""
    if not settings.APP_API_KEY:
        pytest.skip("APP_API_KEY no está configurada")

    payload = {"prompt": "Consulta no autorizada de Burp Suite"}
    response = client.post("/api/v1/ai/query", json=payload)
    assert response.status_code == 401
    assert "Acceso no autorizado" in response.json()["detail"]


def test_ai_endpoint_rejects_invalid_api_key():
    """Verifica que una clave falsa de Burp Suite sea rechazada con 401."""
    if not settings.APP_API_KEY:
        pytest.skip("APP_API_KEY no está configurada")

    payload = {"prompt": "Consulta con clave adulterada"}
    response = client.post("/api/v1/ai/query", json=payload, headers={"X-API-KEY": "fake_burp_key_999"})
    assert response.status_code == 401
    assert "inválida" in response.json()["detail"]


def test_ai_endpoint_rejects_oversized_payload():
    """Verifica que un prompt que exceda max_length (3,000 caracteres) sea bloqueado de inmediato con 422."""
    payload = {
        "prompt": "A" * 3500  # Excede los 3,000 permitidos
    }
    response = client.post("/api/v1/ai/query", json=payload, headers=get_auth_headers())
    assert response.status_code == 422


@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY") or not os.getenv("AZURE_OPENAI_ENDPOINT"),
    reason="Credenciales de Azure OpenAI no configuradas en el entorno (ej. runner de CI)",
)
def test_ai_query_endpoint_live():
    """Prueba en vivo contra Azure OpenAI (se ejecuta solo en entornos locales con .env configurado)."""
    payload = {
        "prompt": "¿Cuáles son las 2 partes principales de un contrato de arrendamiento?",
        "contexto": "string",
    }
    response = client.post("/api/v1/ai/query", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    assert len(response.json()["respuesta"]) > 0


def test_legal_ai_service_initializes_with_managed_identity():
    """Verifica que LegalAIService soporte inicialización Passwordless con Managed Identity."""
    import sys
    from unittest.mock import MagicMock

    mock_azure = MagicMock()
    mock_identity = MagicMock()
    mock_identity.get_bearer_token_provider.return_value = lambda: "mock_token"

    original_client = LegalAIService._client
    try:
        LegalAIService._client = None
        with (
            patch.object(settings, "AZURE_OPENAI_ENDPOINT", "https://mock-openai-legaltech.openai.azure.com/"),
            patch.object(settings, "AZURE_OPENAI_API_KEY", None),
            patch.dict(sys.modules, {"azure": mock_azure, "azure.identity": mock_identity}),
            patch("app.services.azure_openai.AzureOpenAI") as mock_openai_cls,
        ):
            mock_client_instance = MagicMock()
            mock_openai_cls.return_value = mock_client_instance

            client_result = LegalAIService.get_client()
            assert client_result == mock_client_instance
            mock_openai_cls.assert_called_once()
            _, kwargs = mock_openai_cls.call_args
            assert "azure_ad_token_provider" in kwargs
    finally:
        LegalAIService._client = original_client


