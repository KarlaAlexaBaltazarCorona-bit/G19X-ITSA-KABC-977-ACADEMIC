"""Módulo de Control de Acceso: API Key global + identidad y roles del usuario.

Este archivo tiene DOS capas de seguridad independientes, que casi siempre se
usan juntas pero resuelven problemas distintos:

1. `verify_api_key` -- ya existía. Protege toda la API de escaneos anónimos
   (Gobuster, Burp Suite) exigiendo el encabezado `X-API-KEY`. No sabe quién
   es la persona, solo que trae la llave correcta de la aplicación cliente.

2. `get_current_user` / `get_or_create_usuario` -- NUEVO. Además de la API Key,
   estas funciones averiguan QUIÉN es la persona (a partir de su token de
   Microsoft Entra ID) y a qué rol interno pertenece (Revisor
   Jurídico, Aprobador Jurídico, Administrador de la Plataforma o Auditor).
   `app/core/roles_guard.py` usa `get_current_user` para exigir un rol
   específico en cada endpoint de negocio (documentos, workflows, etc.).

Nota de seguridad importante: la verificación de la FIRMA del token contra las
llaves públicas (JWKS) de Microsoft solo se activa cuando `ENTRA_CLIENT_ID`
está configurado en el `.env`. Mientras eso no esté configurado
(desarrollo local, pruebas automáticas), el token se decodifica SIN verificar
firma, igual que hacía el cascarón original de `auth.py`. Esto es
intencional para no bloquear a nadie mientras se resuelve el registro en
Azure, pero es OBLIGATORIO configurar `ENTRA_CLIENT_ID` antes de producción:
sin eso, cualquiera podría fabricar un token con el rol que quiera.
"""

import base64
import json
import logging
import secrets
from typing import Any
from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(
    name="X-API-KEY",
    auto_error=False,
    description="Clave secreta de acceso requerida en el encabezado 'X-API-KEY'.",
)


def verify_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """Valida que la solicitud incluya la clave de acceso autorizada, token Bearer o cookie de sesión.

    Utiliza comparación en tiempo constante (compare_digest) para evitar Timing Attacks.
    """
    if authorization and authorization.startswith("Bearer "):
        # Solicitud autenticada con token Bearer
        return "bearer_authenticated"

    # Verificar si el explorador web tiene una cookie de sesión activa
    if request:
        cookie_token = request.cookies.get("plurione_auth_token") or request.cookies.get("access_token")
        if cookie_token:
            return "cookie_authenticated"

    expected_key = settings.APP_API_KEY
    query_key = request.query_params.get("api_key") if request else None
    effective_api_key = api_key or query_key

    if effective_api_key and expected_key and secrets.compare_digest(effective_api_key, expected_key):
        return effective_api_key

    # Si es navegación directa de un navegador web (solicita text/html) y no está autenticado,
    # redirigir limpiamente a la pantalla de autenticación con Microsoft Entra ID (/login)
    accept = request.headers.get("accept", "") if request else ""
    if "text/html" in accept:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )

    if not effective_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acceso no autorizado. Credenciales de acceso no proporcionadas.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acceso no autorizado. Credencial de acceso inválida o revocada.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


# --- Identidad del usuario (Microsoft Entra ID) -----------------------------

# Roles internos válidos -- coinciden con los App Roles creados en Entra ID
ROLES_VALIDOS = {
    "REVISOR_JURIDICO",
    "APROBADOR_JURIDICO",
    "ADMINISTRADOR_PLATAFORMA",
    "AUDITOR",
}

_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}


def _get_jwks(force_refresh: bool = False) -> dict | None:
    """Descarga y cachea las llaves públicas de Microsoft Entra ID.

    Usa el endpoint /common/discovery/v2.0/keys que contiene el conjunto de
    claves públicas globales para validar tokens de cualquier tenant corporativo (multi-tenant).
    Soporta refresco automático en caso de rotación de claves.
    """
    import time
    import requests

    ahora = time.time()
    if not force_refresh and _jwks_cache["keys"] and (ahora - _jwks_cache["fetched_at"] < 43200):
        return _jwks_cache["keys"]

    try:
        discovery_url = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
        respuesta = requests.get(discovery_url, timeout=5)
        respuesta.raise_for_status()
        data = respuesta.json()
        _jwks_cache["keys"] = data
        _jwks_cache["fetched_at"] = ahora
        return data
    except Exception as e:  # pragma: no cover
        logger.error("No se pudo descargar el JWKS de Microsoft Entra ID: %s", e)
        return _jwks_cache.get("keys")


def _decode_token_claims(token: str) -> dict:
    """Extrae y valida los claims de un token JWT emitido por Microsoft Entra ID.

    - Si `ENTRA_CLIENT_ID` está configurado:
      * Valida la firma del token con las claves públicas globales (JWKS) de Entra ID (RS256).
      * Valida expiración y audiencia (client_id y api://client_id).
      * Valida emisor multi-tenant (iss) e identificador de inquilino (tid).
      * Si se configuró un tenant específico o lista blanca en ENTRA_ALLOWED_TENANTS, restringe el acceso.
    - Si NO está configurado (desarrollo local / pruebas offline):
      * Decodifica el payload JWT sin validar firma emitiendo una advertencia en log.
    """
    if settings.ENTRA_CLIENT_ID:
        try:
            import jwt as pyjwt  # PyJWT

            jwks = _get_jwks()
            if not jwks:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No fue posible validar el token con Microsoft Entra ID en este momento.",
                )
            header = pyjwt.get_unverified_header(token)
            kid = header.get("kid")

            clave_publica = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    clave_publica = pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                    break

            # Si no se encontró el kid, intentar un refresco inmediato de JWKS por rotación de claves
            if clave_publica is None:
                jwks = _get_jwks(force_refresh=True)
                if jwks:
                    for jwk in jwks.get("keys", []):
                        if jwk.get("kid") == kid:
                            clave_publica = pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                            break

            if clave_publica is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="El token fue firmado con una llave no reconocida por Microsoft Entra ID.",
                )

            # Validar firma, tiempo de expiración y audiencia
            audiences = [settings.ENTRA_CLIENT_ID, f"api://{settings.ENTRA_CLIENT_ID}"]
            claims = pyjwt.decode(
                token,
                key=clave_publica,
                algorithms=["RS256"],
                audience=audiences,
                options={"verify_exp": True},
            )

            # Validación de emisor multi-tenant:
            # v2: https://login.microsoftonline.com/{tid}/v2.0
            # v1: https://sts.windows.net/{tid}/
            tid = claims.get("tid")
            iss = claims.get("iss", "")
            if not tid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="El token no contiene el identificador de inquilino (tid).",
                )

            valid_v2 = f"https://login.microsoftonline.com/{tid}/v2.0"
            valid_v1 = f"https://sts.windows.net/{tid}/"
            if iss not in (valid_v2, valid_v1):
                logger.warning("Emisor no reconocido para tenant %s: %s", tid, iss)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="El emisor del token de Microsoft Entra ID no es válido.",
                )

            # Validación de modo Single-Tenant si el administrador configuró un tenant ID específico
            tenant_conf = (settings.ENTRA_TENANT_ID or "").strip().lower()
            if tenant_conf and tenant_conf not in ("common", "organizations"):
                if tid.lower() != tenant_conf:
                    logger.warning("Acceso denegado: tenant %s no coincide con el tenant configurado %s", tid, tenant_conf)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Este inquilino corporativo no está autorizado para acceder a este sistema.",
                    )

            # Validación de lista blanca de inquilinos autorizados (Multi-tenant whitelist)
            if settings.ENTRA_ALLOWED_TENANTS:
                allowed = [t.strip().lower() for t in settings.ENTRA_ALLOWED_TENANTS.split(",") if t.strip()]
                if allowed and tid.lower() not in allowed:
                    logger.warning("Acceso denegado: tenant %s no está en la lista de tenants permitidos", tid)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Su organización corporativa no está en la lista de entidades autorizadas.",
                    )

            return claims

        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Validacion de sesion rechazada o expirada: %s", type(e).__name__)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firma o formato de token no válido.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    # --- Modo desarrollo/pruebas: sin ENTRA_CLIENT_ID configurado -----------
    logger.warning(
        "ENTRA_CLIENT_ID no está configurado: decodificando el token SIN verificar "
        "firma. Esto solo es admisible en desarrollo/pruebas locales."
    )
    try:
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Token con estructura JWT no válida.")
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        return json.loads(payload_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma o formato de token no válido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_or_create_usuario(db: Session, claims: dict):
    """Busca al usuario del token en la BD; si es su primer login, lo crea (auto-provisioning).

    Orden de búsqueda:
    1. Por `objeto_id` (oid) -- el identificador estable de Entra ID.
    2. Por `correo` -- cubre el caso de un funcionario pre-registrado a mano
       desde la Pantalla 13 (Usuarios y funcionarios).
    3. Si no existe en ninguna de las dos, se crea con el rol que traiga el
       token (si es uno de los 4 válidos) o `REVISOR_JURIDICO` por defecto.

    Sincroniza roles si el token contiene roles explícitos de Azure App Roles,
    y verifica que la cuenta esté activa.
    """
    import datetime as _dt

    from app.models.user import RolUsuario, Usuario

    oid = claims.get("oid") or claims.get("sub") or ""
    correo = (claims.get("preferred_username") or claims.get("email") or claims.get("upn") or "").lower().strip()
    nombre_completo = (claims.get("name") or correo or "Usuario sin nombre").strip()
    nombre, _, apellido = nombre_completo.partition(" ")
    roles_del_token = [r for r in claims.get("roles", []) if r in ROLES_VALIDOS]

    admin_correo_config = (getattr(settings, "INITIAL_ADMIN_EMAIL", None) or "").lower().strip()
    es_admin_inicial = bool(admin_correo_config and correo == admin_correo_config)

    usuario = None
    if oid:
        usuario = db.query(Usuario).filter(Usuario.objeto_id == oid).first()
    if usuario is None and correo:
        usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
        if usuario and oid and (not usuario.objeto_id or usuario.objeto_id.startswith("pending-") or usuario.objeto_id.startswith("sin-oid-")):
            usuario.objeto_id = oid

    if usuario is None:
        if es_admin_inicial:
            rol_inicial = RolUsuario.ADMINISTRADOR_PLATAFORMA
        elif roles_del_token:
            rol_inicial = RolUsuario(roles_del_token[0])
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: Su cuenta no ha sido dada de alta por el Administrador de la plataforma.",
            )

        usuario = Usuario(
            objeto_id=oid or f"sin-oid-{correo}",
            nombre=nombre or "Usuario",
            apellido=apellido or None,
            correo=correo or f"{oid}@sin-correo.local",
            role=rol_inicial,
            activo=True,
        )
        db.add(usuario)
    else:
        if es_admin_inicial:
            usuario.role = RolUsuario.ADMINISTRADOR_PLATAFORMA
        elif roles_del_token:
            usuario.role = RolUsuario(roles_del_token[0])

    usuario.ultima_vez = _dt.datetime.now(_dt.UTC)
    db.commit()
    db.refresh(usuario)

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta de usuario inactiva o desactivada. Contacte al Administrador.",
        )

    return usuario


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> dict:
    """Dependencia de FastAPI: identifica al usuario autenticado y su rol interno.

    Soporta:
    1. Token Bearer de Microsoft Entra ID en cabecera 'Authorization: Bearer <token>'
    2. Cookie de sesión activa 'plurione_auth_token' para navegación en el portal web
    3. Llave 'X-API-KEY' para llamadas sistema a sistema (Power BI / automatizaciones CI)
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif request:
        token = request.cookies.get("plurione_auth_token") or request.cookies.get("access_token")

    if not token:
        # Si se envió una API Key válida y no hay sesión de usuario interactivo,
        # autenticar como cuenta de servicio del sistema con rol de administrador
        if api_key and settings.APP_API_KEY and secrets.compare_digest(api_key, settings.APP_API_KEY):
            return {
                "id": "00000000-0000-0000-0000-000000000000",
                "nombre": "Servicio de Integración",
                "correo": "system@legaltech.local",
                "rol": "ADMINISTRADOR_PLATAFORMA",
                "activo": True,
                "tenant_id": "system",
            }

        # Si es navegación directa de navegador (pide text/html), redirigir limpiamente a /login
        accept = request.headers.get("accept", "") if request else ""
        if "text/html" in accept:
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/login"},
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer ausente o no válido. Inicie sesión con Microsoft Entra ID.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _decode_token_claims(token)
    usuario = get_or_create_usuario(db, claims)

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta de usuario inactiva o desactivada. Contacte al Administrador.",
        )

    return {
        "id": str(usuario.id),
        "nombre": usuario.nombre_completo,
        "correo": usuario.correo,
        "rol": usuario.role.value,
        "activo": usuario.activo,
        "tenant_id": claims.get("tid", ""),
    }
