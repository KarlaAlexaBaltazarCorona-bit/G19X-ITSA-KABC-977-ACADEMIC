"""Módulo de Autenticación, Roles y Microsoft Entra ID.

La lógica de decodificar el token y de crear/encontrar al usuario en la BD
vive en `app/core/auth_guard.py` (compartida con `requiere_roles(...)`, que
protege el resto de los endpoints de negocio). Este archivo solo expone las
rutas públicas: la página de login, la config pública de MSAL, y "quién soy".
"""

from pathlib import Path
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth_guard import ROLES_VALIDOS, _decode_token_claims, get_or_create_usuario, verify_api_key
from app.core.config import settings
from app.core.database import get_db

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"


class SessionTokenRequest(BaseModel):
    token: str = Field(..., min_length=1)


class DevLoginRequest(BaseModel):
    rol: str = Field(default="REVISOR_JURIDICO")
    correo: str = Field(default="usuario@plurione.com")
    nombre: str = Field(default="Usuario Corporativo")


@router.get("/login", summary="Pantalla interactiva de Microsoft Entra ID", response_class=HTMLResponse)
def get_login_page():
    """Sirve la interfaz web de Single Sign-On (SSO) con Microsoft Entra ID."""
    html_file = TEMPLATES_DIR / "login.html"
    if not html_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla de login no encontrada.",
        )
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@router.get("/config", summary="Configuración pública de Microsoft Entra ID")
def get_entra_config():
    """Retorna los parámetros necesarios para inicializar MSAL en el navegador.

    En modo multi-tenant corporativo, el authority apunta a /organizations, lo cual permite
    autenticar usuarios de cualquier tenant empresarial (el tenant del desarrollador y otros tenants clientes).
    """
    tenant = (settings.ENTRA_TENANT_ID or "organizations").strip()
    authority = f"https://login.microsoftonline.com/{tenant}"
    return {
        "client_id": settings.ENTRA_CLIENT_ID or "",
        "authority": authority,
        "tenant_id": tenant,
        "is_configured": bool(settings.ENTRA_CLIENT_ID),
        "is_multi_tenant": tenant.lower() in ("common", "organizations"),
        "project_name": settings.PROJECT_NAME,
    }




@router.get("/me", summary="Datos del usuario actual")
def read_current_user(
    request: Request,
    response: Response,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Obtiene el perfil y rol del usuario activo autenticado con Microsoft Entra ID.

    Soporta autenticación mediante Header Authorization Bearer o cookie de sesión 'plurione_auth_token'.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif request:
        token = request.cookies.get("plurione_auth_token") or request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer ausente o no válido. Inicie sesión con Microsoft Entra ID.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _decode_token_claims(token)
    usuario = get_or_create_usuario(db, claims)

    # Asegurar la persistencia de la cookie de sesión en el navegador
    response.set_cookie(
        key="plurione_auth_token",
        value=token,
        max_age=86400,
        path="/",
        samesite="lax",
        httponly=False,
    )

    return {
        "authenticated": True,
        "id": str(usuario.id),
        "name": usuario.nombre_completo,
        "email": usuario.correo,
        "roles": [usuario.role.value],
        "tenant_id": claims.get("tid", ""),
    }


@router.post("/session", summary="Registrar sesión activa en cookies desde el cliente")
def establish_session(payload: SessionTokenRequest, response: Response, db: Session = Depends(get_db)):
    """Valida el token recibido tras el login de MSAL y establece la cookie de sesión."""
    claims = _decode_token_claims(payload.token)
    usuario = get_or_create_usuario(db, claims)

    response.set_cookie(
        key="plurione_auth_token",
        value=payload.token,
        max_age=86400,
        path="/",
        samesite="lax",
        httponly=False,
    )

    return {
        "authenticated": True,
        "name": usuario.nombre_completo,
        "email": usuario.correo,
        "roles": [usuario.role.value],
        "tenant_id": claims.get("tid", ""),
    }


@router.post("/logout", summary="Cerrar sesión y limpiar cookies")
def logout(response: Response):
    """Elimina las cookies de sesión del navegador."""
    response.delete_cookie(key="plurione_auth_token", path="/")
    response.delete_cookie(key="access_token", path="/")
    return {"status": "logged_out", "detail": "Sesión finalizada exitosamente."}


@router.post("/dev-login", summary="Inicio de sesión para desarrollo local (solo activo cuando ENTRA_CLIENT_ID no está configurado)")
def dev_login(payload: DevLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Permite verificar roles y pantallas en entornos locales mientras se completa el registro en Azure."""
    import os

    is_production = bool(os.getenv("WEBSITE_HOSTNAME")) or os.getenv("ENVIRONMENT", "").lower() == "production"
    if is_production or settings.ENTRA_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El inicio de sesión simulado de prueba está desactivado en producción. Autentíquese con Microsoft Entra ID institucional.",
        )

    import base64
    import json
    import time

    rol_elegido = payload.rol if payload.rol in ROLES_VALIDOS else "REVISOR_JURIDICO"
    claims = {
        "oid": f"dev-oid-{rol_elegido.lower()}",
        "tid": "dev-tenant-plurione",
        "preferred_username": payload.correo,
        "name": f"{payload.nombre} ({rol_elegido.replace('_', ' ').title()})",
        "roles": [rol_elegido],
        "exp": int(time.time()) + 86400,
    }
    header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    mock_token = f"{header_b64}.{payload_b64}."

    usuario = get_or_create_usuario(db, claims)
    response.set_cookie(
        key="plurione_auth_token",
        value=mock_token,
        max_age=86400,
        path="/",
        samesite="lax",
        httponly=False,
    )

    return {
        "authenticated": True,
        "token": mock_token,
        "name": usuario.nombre_completo,
        "email": usuario.correo,
        "roles": [usuario.role.value],
    }


@router.post("/sanitize-database", summary="Ejecuta saneamiento forzado de base de datos (requiere API Key)")
def trigger_database_sanitization(
    db: Session = Depends(get_db),
    api_key_check: str = Depends(verify_api_key),
):
    """Ejecuta de manera controlada el saneamiento de cuentas heredadas y restablece la gobernanza."""
    try:
        from app.core.database import seed_initial_admin
        from app.models.user import Usuario

        seed_initial_admin()
        usuarios_actuales = [u.correo for u in db.query(Usuario).all()]
        return {"status": "success", "detail": "Saneamiento de base de datos ejecutado con éxito.", "usuarios_restantes": usuarios_actuales}
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
