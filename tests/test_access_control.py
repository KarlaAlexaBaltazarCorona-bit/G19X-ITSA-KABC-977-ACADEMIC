"""Pruebas exhaustivas del Control de Acceso (RBAC), Sesiones por Cookie,
Auto-provisioning y Validación de Tokens Multi-Tenant de Microsoft Entra ID.
"""

import base64
import json
import time
import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.auth_guard import (
    _decode_token_claims,
    get_current_user,
    get_or_create_usuario,
)
from app.core.config import settings
from app.models.solicitud import EstadoSolicitud, PrioridadSolicitud, SolicitudRevision
from app.models.tenant import TenantModel
from app.models.user import RolUsuario, Usuario
from main import app


def _crear_token_jwt_prueba(
    oid: str = "oid-test-1234",
    tid: str = "tenant-corp-test",
    correo: str = "abogado@empresa-externa.com",
    nombre: str = "Lic. Juan Pérez",
    roles: list[str] | None = None,
    iss: str | None = None,
    exp: int | None = None,
) -> str:
    """Genera un token JWT estructurado con claims de Entra ID."""
    if exp is None:
        exp = int(time.time()) + 3600
    if iss is None:
        iss = f"https://login.microsoftonline.com/{tid}/v2.0"
    if roles is None:
        roles = ["REVISOR_JURIDICO"]

    claims = {
        "oid": oid,
        "tid": tid,
        "preferred_username": correo,
        "name": nombre,
        "roles": roles,
        "iss": iss,
        "exp": exp,
    }
    header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}."


# ─────────────────────────────────────────────────────────────────────────────
# 1. PRUEBAS DE CONFIGURACIÓN Y ENDPOINTS DE AUTH
# ─────────────────────────────────────────────────────────────────────────────

def test_auth_config_multi_tenant(client: TestClient):
    """Verifica que /auth/config reporte modo Multi-Tenant."""
    res = client.get("/api/v1/auth/config")
    assert res.status_code == 200
    data = res.json()
    assert data["is_multi_tenant"] is True
    assert data["tenant_id"] in ("common", "organizations")
    assert "login.microsoftonline.com" in data["authority"]


def test_auth_session_and_logout(client: TestClient, db):
    """Verifica el establecimiento de sesión por cookie y su eliminación con logout."""
    token = _crear_token_jwt_prueba(
        oid="oid-session-user",
        tid="tenant-a",
        correo="sesion@corporativo.com",
        roles=["AUDITOR"],
    )

    try:
        with patch.object(settings, "ENTRA_CLIENT_ID", None):
            # 1. Establecer sesión
            res_session = client.post("/api/v1/auth/session", json={"token": token})
            assert res_session.status_code == 200
            assert "plurione_auth_token" in res_session.headers.get("set-cookie", "")

            # 2. Cerrar sesión
            res_logout = client.post("/api/v1/auth/logout")
            assert res_logout.status_code == 200
            assert "plurione_auth_token=" in res_logout.headers.get("set-cookie", "")
    finally:
        db.query(Usuario).filter(Usuario.objeto_id == "oid-session-user").delete()
        db.commit()


def test_dev_login_simulation(client: TestClient, db):
    """Verifica que el login simulado para desarrollo funcione cuando ENTRA_CLIENT_ID está vacío."""
    try:
        with patch.object(settings, "ENTRA_CLIENT_ID", None):
            res = client.post("/api/v1/auth/dev-login", json={"rol": "AUDITOR", "correo": "auditor@local.test"})
            assert res.status_code == 200
            data = res.json()
            assert data["authenticated"] is True
            assert "AUDITOR" in data["roles"]
            assert "plurione_auth_token" in res.headers.get("set-cookie", "")
    finally:
        db.query(Usuario).filter(Usuario.correo == "auditor@local.test").delete()
        db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 2. PRUEBAS DE CONTROL DE ACCESO POR ROL (RBAC)
# ─────────────────────────────────────────────────────────────────────────────

def test_rbac_revisor_cannot_decide_solicitud(client: TestClient, db):
    """Un REVISOR_JURIDICO no tiene permiso para aprobar/rechazar solicitudes (Pantalla 9)."""
    # Crear usuario revisor en BD
    revisor = Usuario(
        id=uuid.uuid4(),
        objeto_id="oid-revisor-rbac",
        correo="revisor_rbac@corp.com",
        nombre="Carlos Revisor",
        role=RolUsuario.REVISOR_JURIDICO,
        activo=True,
    )
    db.add(revisor)

    solicitud = SolicitudRevision(
        id=uuid.uuid4(),
        numero_respuesta="EXP-RBAC-001",
        titulo="Contrato Prueba RBAC",
        tipo_documento="contrato",
        prioridad=PrioridadSolicitud.NORMAL,
        estado=EstadoSolicitud.EN_APROBACION,
        requested_id=revisor.id,
    )
    db.add(solicitud)
    db.commit()

    # Sobreescribir usuario actual como Revisor
    app.dependency_overrides[get_current_user] = lambda: {
        "id": str(revisor.id),
        "nombre": revisor.nombre_completo,
        "correo": revisor.correo,
        "rol": "REVISOR_JURIDICO",
        "activo": True,
    }

    try:
        res = client.post(
            f"/api/v1/solicitudes/{solicitud.id}/decision",
            json={"decision": "aprobar", "motivo": "Intento no autorizado"},
        )
        assert res.status_code == 403
        assert "no tiene permiso" in res.json()["detail"]
    finally:
        from app.models.audit import Auditoria
        app.dependency_overrides.pop(get_current_user, None)
        db.query(Auditoria).filter(Auditoria.solicitud_id == solicitud.id).delete()
        db.query(SolicitudRevision).filter(SolicitudRevision.id == solicitud.id).delete()
        db.query(Usuario).filter(Usuario.id == revisor.id).delete()
        db.commit()


def test_rbac_aprobador_can_decide_solicitud(client: TestClient, db):
    """Un APROBADOR_JURIDICO sí tiene permiso para aprobar solicitudes."""
    aprobador = Usuario(
        id=uuid.uuid4(),
        objeto_id="oid-aprobador-rbac",
        correo="aprobador@corp.com",
        nombre="Dra. Laura Aprobadora",
        role=RolUsuario.APROBADOR_JURIDICO,
        activo=True,
    )
    db.add(aprobador)

    solicitud = SolicitudRevision(
        id=uuid.uuid4(),
        numero_respuesta="EXP-RBAC-002",
        titulo="Contrato Prueba Aprobador",
        tipo_documento="contrato",
        prioridad=PrioridadSolicitud.NORMAL,
        estado=EstadoSolicitud.EN_APROBACION,
        requested_id=aprobador.id,
    )
    db.add(solicitud)
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: {
        "id": str(aprobador.id),
        "nombre": aprobador.nombre_completo,
        "correo": aprobador.correo,
        "rol": "APROBADOR_JURIDICO",
        "activo": True,
    }

    try:
        res = client.post(
            f"/api/v1/solicitudes/{solicitud.id}/decision",
            json={"decision": "aprobar", "motivo": "Aprobación legal formal"},
        )
        assert res.status_code == 200
        assert res.json()["estado"] == EstadoSolicitud.APROBADO.value
    finally:
        from app.models.audit import Auditoria
        app.dependency_overrides.pop(get_current_user, None)
        db.query(Auditoria).filter(Auditoria.solicitud_id == solicitud.id).delete()
        db.query(SolicitudRevision).filter(SolicitudRevision.id == solicitud.id).delete()
        db.query(Usuario).filter(Usuario.id == aprobador.id).delete()
        db.commit()


def test_rbac_auditor_can_view_audit_trail(client: TestClient, db):
    """Un AUDITOR tiene acceso a la trazabilidad de expedientes (Pantalla 11)."""
    auditor = Usuario(
        id=uuid.uuid4(),
        objeto_id="oid-auditor-rbac",
        correo="auditor@corp.com",
        nombre="Auditor Interno",
        role=RolUsuario.AUDITOR,
        activo=True,
    )
    solicitud_id = uuid.uuid4()

    app.dependency_overrides[get_current_user] = lambda: {
        "id": str(auditor.id),
        "nombre": auditor.nombre_completo,
        "correo": auditor.correo,
        "rol": "AUDITOR",
        "activo": True,
    }

    try:
        res = client.get(f"/api/v1/audit/trail/{solicitud_id}")
        assert res.status_code == 200
        assert isinstance(res.json(), list)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_rbac_revisor_cannot_view_audit_trail(client: TestClient):
    """Un REVISOR_JURIDICO no puede consultar la bitácora de auditoría detallada (requiere AUDITOR o ADMIN)."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": str(uuid.uuid4()),
        "nombre": "Revisor",
        "correo": "revisor@test.local",
        "rol": "REVISOR_JURIDICO",
        "activo": True,
    }

    try:
        res = client.get(f"/api/v1/audit/trail/{uuid.uuid4()}")
        assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# 3. PRUEBAS DE INACTIVIDAD DE USUARIO Y VALIDACIÓN DE TOKEN
# ─────────────────────────────────────────────────────────────────────────────

def test_inactive_user_is_blocked_403(db):
    """Un usuario con activo=False es bloqueado con 403 aunque su token sea válido."""
    usuario_inactivo = Usuario(
        id=uuid.uuid4(),
        objeto_id="oid-usuario-inactivo-123",
        correo="inactivo@corp.com",
        nombre="Usuario Inactivo",
        role=RolUsuario.REVISOR_JURIDICO,
        activo=False,
    )
    db.add(usuario_inactivo)
    db.commit()

    claims = {
        "oid": "oid-usuario-inactivo-123",
        "preferred_username": "inactivo@corp.com",
        "name": "Usuario Inactivo",
        "roles": ["REVISOR_JURIDICO"],
    }

    try:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_or_create_usuario(db, claims)
        assert exc_info.value.status_code == 403
        assert "desactivada" in exc_info.value.detail or "inactiva" in exc_info.value.detail
    finally:
        db.delete(usuario_inactivo)
        db.commit()


def test_auto_provisioning_creates_new_user(db):
    """Si el usuario de Entra ID inicia sesión por primera vez, se auto-crea en la BD."""
    claims = {
        "oid": "oid-nuevo-empleado-999",
        "tid": "tenant-corp-plurione",
        "preferred_username": "nuevo.abogado@plurione.com",
        "name": "Lic. Mario Moreno",
        "roles": ["REVISOR_JURIDICO"],
    }

    usuario = get_or_create_usuario(db, claims)
    try:
        assert usuario.objeto_id == "oid-nuevo-empleado-999"
        assert usuario.correo == "nuevo.abogado@plurione.com"
        assert usuario.role == RolUsuario.REVISOR_JURIDICO
        assert usuario.activo is True
        assert usuario.ultima_vez is not None
    finally:
        db.delete(usuario)
        db.commit()


def test_unregistered_user_without_roles_is_rejected(db):
    """Cuentas personales o externas sin pre-registro en la plataforma son rechazadas con 403."""
    claims = {
        "oid": "oid-externo-desconocido-111",
        "tid": "tenant-externo",
        "preferred_username": "cuenta.personal@gmail.com",
        "name": "Persona Externa",
        "roles": [],
    }

    with pytest.raises(HTTPException) as exc_info:
        get_or_create_usuario(db, claims)

    assert exc_info.value.status_code == 403
    assert "No ha sido dada de alta" in exc_info.value.detail or "Acceso denegado" in exc_info.value.detail


# ─────────────────────────────────────────────────────────────────────────────
# 4. PRUEBAS MULTI-TENANT DE EMISOR Y RESTRICCIÓN DE TENANTS
# ─────────────────────────────────────────────────────────────────────────────

def test_multi_tenant_issuer_validation():
    """Valida la aceptación de tokens de distintos inquilinos corporativos."""
    # Simular ENTRA_CLIENT_ID configurado con llaves simuladas
    with (
        patch.object(settings, "ENTRA_CLIENT_ID", "mock-client-id"),
        patch.object(settings, "ENTRA_TENANT_ID", "organizations"),
        patch("app.core.auth_guard._get_jwks", return_value={"keys": [{"kid": "k1", "kty": "RSA"}]}),
        patch("jwt.get_unverified_header", return_value={"kid": "k1"}),
        patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value="mock-key"),
    ):
        # 1. Tenant corporativo A (v2)
        claims_tenant_a = {
            "tid": "tenant-alpha-uuid",
            "iss": "https://login.microsoftonline.com/tenant-alpha-uuid/v2.0",
            "aud": "mock-client-id",
            "oid": "oid-user-a",
            "preferred_username": "user@alpha.com",
        }
        with patch("jwt.decode", return_value=claims_tenant_a):
            decoded_a = _decode_token_claims("dummy.token.here")
            assert decoded_a["tid"] == "tenant-alpha-uuid"

        # 2. Tenant corporativo B (v2)
        claims_tenant_b = {
            "tid": "tenant-beta-uuid",
            "iss": "https://login.microsoftonline.com/tenant-beta-uuid/v2.0",
            "aud": "mock-client-id",
            "oid": "oid-user-b",
            "preferred_username": "user@beta.com",
        }
        with patch("jwt.decode", return_value=claims_tenant_b):
            decoded_b = _decode_token_claims("dummy.token.here")
            assert decoded_b["tid"] == "tenant-beta-uuid"

        # 3. Emisor no válido debe ser rechazado
        from fastapi import HTTPException
        claims_forged = {
            "tid": "tenant-alpha-uuid",
            "iss": "https://malicious-sts.attacker.com/v2.0",
            "aud": "mock-client-id",
        }
        with patch("jwt.decode", return_value=claims_forged):
            with pytest.raises(HTTPException) as exc_info:
                _decode_token_claims("dummy.token.here")
            assert exc_info.value.status_code == 401


def test_single_tenant_restriction():
    """Si ENTRA_TENANT_ID está configurado a un GUID específico, rechaza otros tenants."""
    from fastapi import HTTPException

    mi_tenant = "11111111-2222-3333-4444-555555555555"
    otro_tenant = "99999999-8888-7777-6666-555555555555"

    with (
        patch.object(settings, "ENTRA_CLIENT_ID", "mock-client-id"),
        patch.object(settings, "ENTRA_TENANT_ID", mi_tenant),
        patch("app.core.auth_guard._get_jwks", return_value={"keys": [{"kid": "k1", "kty": "RSA"}]}),
        patch("jwt.get_unverified_header", return_value={"kid": "k1"}),
        patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value="mock-key"),
    ):
        claims_otro = {
            "tid": otro_tenant,
            "iss": f"https://login.microsoftonline.com/{otro_tenant}/v2.0",
            "aud": "mock-client-id",
        }
        with patch("jwt.decode", return_value=claims_otro):
            with pytest.raises(HTTPException) as exc_info:
                _decode_token_claims("dummy.token.here")
            assert exc_info.value.status_code == 403
            assert "no está autorizado" in exc_info.value.detail


def test_organizations_endpoint_rbac(client: TestClient, db):
    """El endpoint /api/v1/organizations lista los inquilinos para Administrador."""
    tenant = TenantModel(
        id=uuid.uuid4(),
        nombre_comercial="Grupo México Legal S.A.",
        rfc="GML123456ABC",
        activo=True,
    )
    db.add(tenant)
    db.commit()

    try:
        res = client.get("/api/v1/organizations/")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert any(t["nombre_comercial"] == "Grupo México Legal S.A." for t in data["items"])
    finally:
        db.delete(tenant)
        db.commit()


def test_sqladmin_panel_requires_auth(client: TestClient):
    """Verifica que /admin/usuario/list no sea accesible públicamente y exija autenticación."""
    res = client.get("/admin/usuario/list", follow_redirects=False)
    # Debe responder con redirección hacia el login administrativo o prohibido
    assert res.status_code in (302, 303, 307)
    assert "/admin/login" in res.headers.get("location", "")


def test_powerbi_html_requires_auth_and_redirects_browser(client: TestClient):
    """Verifica que un navegador web en /api/v1/analytics/powerbi-html sea redirigido a /login si no está autenticado."""
    from app.core.auth_guard import get_current_user, verify_api_key

    # Limpiar overrides para probar la seguridad real
    saved_user = app.dependency_overrides.pop(get_current_user, None)
    saved_key = app.dependency_overrides.pop(verify_api_key, None)
    try:
        res = client.get("/api/v1/analytics/powerbi-html", headers={"Accept": "text/html"}, follow_redirects=False)
        assert res.status_code == 307
        assert res.headers.get("location") == "/login"
    finally:
        if saved_user:
            app.dependency_overrides[get_current_user] = saved_user
        if saved_key:
            app.dependency_overrides[verify_api_key] = saved_key

