"""Configuración de pruebas: base de datos SQLite en memoria + usuario de prueba.

Usar SQLite en pruebas (en vez de Postgres real) tiene dos ventajas:
1. Cualquier desarrollador puede correr `pytest` sin tener Postgres levantado.
2. Cada prueba parte de una BD limpia (no deja basura entre tests).

La única diferencia con Postgres que hay que vigilar es que SQLite no soporta
los tipos ENUM nativo ni algunas restricciones de FK tan estrictamente -- pero
para probar la lógica de negocio es más que suficiente.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.database as core_db
import app.main as app_main
from app.core.config import settings
from app.core.database import Base, get_db
from main import app

# Asegurar API Key de prueba para que los tests de autenticación funcionen tanto en local como en CI
if not settings.APP_API_KEY:
    settings.APP_API_KEY = "test-ci-api-key-32chars-minimum-sec"

if not getattr(settings, "APP_ENCRYPTION_KEY", None):
    settings.APP_ENCRYPTION_KEY = "test-encryption-key-32-chars-long!"

if not getattr(settings, "INITIAL_ADMIN_EMAIL", None):
    settings.INITIAL_ADMIN_EMAIL = "admin@plurione.legaltech.com"

# Neutralizar init_db() en tests para que el arranque de FastAPI no intente conectar a Azure Postgres
core_db.init_db = lambda: None
app_main.init_db = lambda: None

# BD SQLite en memoria: se crea y destruye por cada sesión de pruebas.
# StaticPool mantiene una única conexión persistente en memoria para compartir las tablas entre sesiones y peticiones HTTP.
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"
engine_test = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    """Sustituye la sesión real de PostgreSQL por una de SQLite en memoria durante las pruebas."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    """Usuario de prueba con rol ADMINISTRADOR_PLATAFORMA para que todos los endpoints sean accesibles."""
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "nombre": "Admin de Pruebas",
        "correo": "admin@test.local",
        "rol": "ADMINISTRADOR_PLATAFORMA",
        "activo": True,
    }


@pytest.fixture(scope="session", autouse=True)
def mock_external_azure_services():
    """Evita llamadas de red lentas o fallidas a Azure Blob Storage e Intelligence en pruebas."""
    from unittest.mock import patch

    with (
        patch("app.services.azure_blob.AzureBlobService.upload_file", return_value="https://test.blob.core.windows.net/test/test.pdf"),
        patch("app.services.azure_doc_intel.DocumentIntelligenceService.extract_clauses_from_pdf", return_value={"texto": "", "clausulas": []}),
        patch("app.services.azure_openai.LegalAIService.clasificar_area", return_value="Civil / Mercantil"),
    ):
        yield


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Crea todas las tablas antes de correr las pruebas y las elimina al terminar."""
    # Importar modelos para que queden registrados en Base.metadata
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db():
    """Sesión de BD SQLite en memoria para usar directamente en pruebas unitarias."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Cliente HTTP de prueba con la BD y el usuario sobreescritos."""
    from app.core.auth_guard import get_current_user, verify_api_key
    from app.core.rate_limiter import rate_limit_guard

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[verify_api_key] = lambda: True
    app.dependency_overrides[rate_limit_guard] = lambda: True
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
