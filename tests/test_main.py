from fastapi.testclient import TestClient
from main import app
from app.core.config import settings

client = TestClient(app)


def get_auth_headers() -> dict[str, str]:
    if settings.APP_API_KEY:
        return {"X-API-KEY": settings.APP_API_KEY}
    return {}


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_read_root_browser_redirect():
    """Verifica que un navegador web en / sea redirigido al portal /login."""
    response = client.get("/", headers={"Accept": "text/html"}, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers.get("location") == "/login"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_security_headers_present():
    """Verifica que se elimine la firma de uvicorn y existan cabeceras OWASP."""
    response = client.get("/health")
    assert "server" not in response.headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_info_endpoint_requires_auth_when_configured():
    # Sin clave debe responder 401
    res_unauth = client.get("/api/info")
    assert res_unauth.status_code == 401

    # Con clave autorizada debe responder 200
    res_auth = client.get("/api/info", headers=get_auth_headers())
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert data["status"] == "operational"
    # Comprobar que no se expongan URLs ni metadatos de arquitectura
    assert "https://" not in str(data)
    assert "azure" not in str(data).lower()


def test_api_v1_router_mounted_and_protected():
    from app.core.auth_guard import get_current_user
    from app.core.database import get_db
    from tests.conftest import override_get_current_user, override_get_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        if settings.APP_API_KEY:
            # Bloqueo contra escaneos de Gobuster sin autenticación (falta X-API-KEY)
            res_unauth = client.get("/api/v1/solicitudes/")
            assert res_unauth.status_code == 401

        # Acceso permitido con credencial autorizada
        res_auth = client.get("/api/v1/solicitudes/", headers=get_auth_headers())
        assert res_auth.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_login_page_renders():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Microsoft Entra ID" in response.text
    # Previene filtración de datos ficticios o cascarones post-login en HTML público
    assert "usuario@institucion.edu.mx" not in response.text
    assert "ASESOR_JURIDICO" not in response.text
    assert "auth-card" not in response.text
    assert "/static/js/auth.js" in response.text


def test_static_auth_js_served():
    """Verifica que el script modular de autenticación se sirva con cabeceras de caché."""
    response = client.get("/static/js/auth.js")
    assert response.status_code == 200
    assert "msalInstance" in response.text
    assert "public, max-age=" in response.headers.get("cache-control", "")


def test_404_renders_html_for_browser_requests():
    """Verifica que un navegador web reciba la pantalla HTML corporativa en vez de JSON expuesto."""
    response = client.get("/non-existent-probe-url", headers={"Accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 404
    assert "text/html" in response.headers.get("content-type", "")
    assert "PluriOne LegalTech" in response.text
    assert "404" in response.text
    assert "server" not in response.headers


def test_404_renders_json_for_api_clients():
    """Verifica que un cliente API o escáner reciba JSON limpio sin stack traces."""
    response = client.get("/non-existent-probe-url", headers={"Accept": "application/json"})
    assert response.status_code == 404
    assert "application/json" in response.headers.get("content-type", "")
    data = response.json()
    assert "detail" in data
    assert "Traceback" not in str(data)

