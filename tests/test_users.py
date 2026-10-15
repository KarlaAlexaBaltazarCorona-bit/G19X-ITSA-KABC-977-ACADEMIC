"""Pruebas del endpoint /auth/me."""

from fastapi.testclient import TestClient


def test_me_sin_token_devuelve_401(client: TestClient):
    """Sin token Bearer, /auth/me debe devolver 401."""
    from app.core.auth_guard import get_current_user
    from main import app

    # Limpiar cualquier override previo para ejecutar la validación estándar
    saved = app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    finally:
        if saved:
            app.dependency_overrides[get_current_user] = saved


def test_initial_admin_role_provisioning(db):
    """Verifica que la cuenta administradora inicial configurada reciba el rol ADMINISTRADOR_PLATAFORMA."""
    from app.core.auth_guard import get_or_create_usuario
    from app.core.config import settings
    from app.models.user import RolUsuario

    admin_email = settings.INITIAL_ADMIN_EMAIL.lower().strip()
    claims = {
        "oid": "oid-initial-admin-test",
        "email": admin_email,
        "name": "Administrador Plataforma",
    }
    usuario = get_or_create_usuario(db, claims)
    assert usuario.correo == admin_email
    assert usuario.role == RolUsuario.ADMINISTRADOR_PLATAFORMA
    assert usuario.activo is True
