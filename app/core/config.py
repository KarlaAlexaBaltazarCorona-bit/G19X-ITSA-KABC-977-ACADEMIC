import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configuración global del sistema cargada desde variables de entorno."""

    PROJECT_NAME: str = "Plataforma de Workflow para Revisión Jurídica"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Base de Datos PostgreSQL
    POSTGRES_URL: str | None = os.getenv("POSTGRES_URL")

    # Servicios Azure
    AZURE_OPENAI_ENDPOINT: str | None = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY: str | None = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-mini")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    AZURE_OPENAI_MAX_TOKENS: int = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "1000"))
    AZURE_OPENAI_REASONING_EFFORT: str = os.getenv("AZURE_OPENAI_REASONING_EFFORT", "low")
    AZURE_SEARCH_ENDPOINT: str | None = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_KEY: str | None = os.getenv("AZURE_SEARCH_KEY")
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str | None = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str | None = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    AZURE_STORAGE_ACCOUNT_NAME: str = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "almacenlegalprojectia")
    AZURE_STORAGE_CONTAINER_NAME: str = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "documentos")
    AZURE_STORAGE_CONNECTION_STRING: str | None = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    # Seguridad, Control de Acceso y Límites
    APP_ENCRYPTION_KEY: str | None = os.getenv("APP_ENCRYPTION_KEY")
    APP_API_KEY: str = os.getenv("APP_API_KEY", "")
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1")
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "2400"))
    MAX_REQUEST_BODY_BYTES: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(10 * 1024 * 1024)))  # 10 MB


    # Microsoft Entra ID (SSO Institucional / Corporativo Multi-Tenant y Cuentas Personales)
    ENTRA_CLIENT_ID: str | None = os.getenv("ENTRA_CLIENT_ID", "d821b328-badf-4b25-b254-58adb089ab81")
    ENTRA_TENANT_ID: str = os.getenv("ENTRA_TENANT_ID", "common")
    # Opcional: lista separada por comas de tenant IDs autorizados (whitelist multi-tenant).
    ENTRA_ALLOWED_TENANTS: str | None = os.getenv("ENTRA_ALLOWED_TENANTS")

    # Administración Inicial de la Plataforma
    INITIAL_ADMIN_EMAIL: str = os.getenv("INITIAL_ADMIN_EMAIL", "isc221977@itsatlixco.edu.mx")

    # Documentación API (Ocultar en producción)
    ENABLE_DOCS: bool = os.getenv("ENABLE_DOCS", "false").lower() in ("true", "1")


settings = Settings()
