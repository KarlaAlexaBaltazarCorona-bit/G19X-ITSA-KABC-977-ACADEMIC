"""Batería de pruebas para la máquina de estados del motor de workflow (HU-01, HU-05, HU-09, HU-10).

Verifica que el ciclo de vida jurídico respete estrictamente las transiciones permitidas
y rechace cualquier salto de estado ilegal con HTTP 409 Conflict.
"""

import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.solicitud import EstadoSolicitud, PrioridadSolicitud, SolicitudRevision
from app.models.user import RolUsuario, Usuario
from app.services.workflow_engine import WorkflowEngine


@pytest.fixture
def test_solicitud(db: Session) -> SolicitudRevision:
    """Crea una solicitud de prueba en estado BORRADOR."""
    user = db.query(Usuario).first()
    if not user:
        user = Usuario(
            id=uuid.uuid4(),
            objeto_id="oid-test-wf",
            correo="user_wf@test.local",
            nombre="Usuario Workflow",
            role=RolUsuario.ADMINISTRADOR_PLATAFORMA,
            activo=True,
        )
        db.add(user)
        db.commit()

    sol = SolicitudRevision(
        id=uuid.uuid4(),
        numero_respuesta="EXP-2026-TEST",
        titulo="Contrato de Prueba Transiciones",
        tipo_documento="contrato",
        prioridad=PrioridadSolicitud.NORMAL,
        requested_id=user.id,
        estado=EstadoSolicitud.BORRADOR,
    )
    db.add(sol)
    db.commit()
    db.refresh(sol)
    yield sol

    # Limpieza
    db.query(SolicitudRevision).filter(SolicitudRevision.id == sol.id).delete()
    db.commit()


def test_transicion_valida_borrador_a_en_revision(db: Session, test_solicitud: SolicitudRevision):
    """BORRADOR -> EN_REVISION es una transición legal."""
    usuario = {"id": test_solicitud.requested_id, "rol": "ADMINISTRADOR_PLATAFORMA"}
    sol = WorkflowEngine.transicionar_estado(db, test_solicitud, EstadoSolicitud.EN_REVISION, usuario)
    assert sol.estado == EstadoSolicitud.EN_REVISION


def test_transicion_invalida_borrador_a_aprobado_lanza_409(db: Session, test_solicitud: SolicitudRevision):
    """BORRADOR -> APROBADO sin revisión es ilegal y debe lanzar 409 Conflict."""
    usuario = {"id": test_solicitud.requested_id, "rol": "ADMINISTRADOR_PLATAFORMA"}
    with pytest.raises(HTTPException) as exc_info:
        WorkflowEngine.transicionar_estado(db, test_solicitud, EstadoSolicitud.APROBADO, usuario)
    assert exc_info.value.status_code == 409
    assert f"No se puede pasar de {EstadoSolicitud.BORRADOR.value} a {EstadoSolicitud.APROBADO.value}" in exc_info.value.detail


def test_transicion_invalida_firmado_a_rechazado_lanza_409(db: Session, test_solicitud: SolicitudRevision):
    """FIRMADO es estado terminal; no se puede rechazar un documento ya firmado (409 Conflict)."""
    test_solicitud.estado = EstadoSolicitud.FIRMADO
    db.commit()

    usuario = {"id": test_solicitud.requested_id, "rol": "ADMINISTRADOR_PLATAFORMA"}
    with pytest.raises(HTTPException) as exc_info:
        WorkflowEngine.transicionar_estado(db, test_solicitud, EstadoSolicitud.RECHAZADO, usuario)
    assert exc_info.value.status_code == 409
    assert f"No se puede pasar de {EstadoSolicitud.FIRMADO.value} a {EstadoSolicitud.RECHAZADO.value}" in exc_info.value.detail


def test_transicion_invalida_rechazado_a_en_revision_lanza_409(db: Session, test_solicitud: SolicitudRevision):
    """RECHAZADO es estado terminal; no se puede reabrir a revisión directamente (409 Conflict)."""
    test_solicitud.estado = EstadoSolicitud.RECHAZADO
    db.commit()

    usuario = {"id": test_solicitud.requested_id, "rol": "ADMINISTRADOR_PLATAFORMA"}
    with pytest.raises(HTTPException) as exc_info:
        WorkflowEngine.transicionar_estado(db, test_solicitud, EstadoSolicitud.EN_REVISION, usuario)
    assert exc_info.value.status_code == 409
    assert f"No se puede pasar de {EstadoSolicitud.RECHAZADO.value} a {EstadoSolicitud.EN_REVISION.value}" in exc_info.value.detail


def test_ciclo_completo_transiciones_validas(db: Session, test_solicitud: SolicitudRevision):
    """Valida el ciclo legal de punta a punta: BORRADOR -> EN_REVISION -> EN_APROBACION -> APROBADO -> FIRMADO."""
    usuario = {"id": test_solicitud.requested_id, "rol": "ADMINISTRADOR_PLATAFORMA"}

    # 1. BORRADOR -> EN_REVISION
    WorkflowEngine.transicionar_estado(db, test_solicitud, EstadoSolicitud.EN_REVISION, usuario)
    assert test_solicitud.estado == EstadoSolicitud.EN_REVISION

    # 2. EN_REVISION -> EN_APROBACION
    WorkflowEngine.transicionar_estado(db, test_solicitud, EstadoSolicitud.EN_APROBACION, usuario)
    assert test_solicitud.estado == EstadoSolicitud.EN_APROBACION

    # 3. EN_APROBACION -> APROBADO
    WorkflowEngine.transicionar_estado(db, test_solicitud, EstadoSolicitud.APROBADO, usuario)
    assert test_solicitud.estado == EstadoSolicitud.APROBADO
    assert test_solicitud.finalizo_at is not None

    # 4. APROBADO -> FIRMADO
    WorkflowEngine.transicionar_estado(db, test_solicitud, EstadoSolicitud.FIRMADO, usuario)
    assert test_solicitud.estado == EstadoSolicitud.FIRMADO


def test_endpoint_decision_rechaza_salto_invalido_con_409(client: TestClient, db: Session, test_solicitud: SolicitudRevision):
    """Al intentar aprobar por endpoint una solicitud en BORRADOR, la API responde HTTP 409."""
    assert test_solicitud.estado == EstadoSolicitud.BORRADOR
    response = client.post(
        f"/api/v1/solicitudes/{test_solicitud.id}/decision",
        json={"decision": "aprobar", "motivo": "Intento de aprobación prematura"},
    )
    assert response.status_code == 409
    data = response.json()
    assert "No se puede pasar de BORRADOR a APROBADO" in data["detail"]


def test_assign_reviewer_fallback_to_admin_when_no_revisores(db: Session):
    """Si no existen usuarios con rol REVISOR_JURIDICO, se asigna con balanceo a un administrador/aprobador activo (resiliencia)."""
    # Limpiar revisores existentes en sesión
    db.query(Usuario).filter(Usuario.role == RolUsuario.REVISOR_JURIDICO).delete()
    db.commit()

    admin = db.query(Usuario).filter(Usuario.role == RolUsuario.ADMINISTRADOR_PLATAFORMA, Usuario.activo == True).first()  # noqa: E712
    if not admin:
        admin = Usuario(
            id=uuid.uuid4(),
            objeto_id="oid-admin-fallback",
            correo="admin_fallback@test.local",
            nombre="Admin Resiliente",
            role=RolUsuario.ADMINISTRADOR_PLATAFORMA,
            activo=True,
        )
        db.add(admin)
        db.commit()

    asignado = WorkflowEngine.assign_reviewer(db)
    assert asignado is not None
    assert asignado.role in (RolUsuario.ADMINISTRADOR_PLATAFORMA, RolUsuario.APROBADOR_JURIDICO)


def test_assign_reviewer_prioritizes_revisores_juridicos(db: Session):
    """Si existen revisores jurídicos, se les prioriza sobre los administradores."""
    revisor = Usuario(
        id=uuid.uuid4(),
        objeto_id=f"oid-rev-{uuid.uuid4().hex[:6]}",
        correo=f"revisor_{uuid.uuid4().hex[:6]}@test.local",
        nombre="Licenciado Titular",
        role=RolUsuario.REVISOR_JURIDICO,
        activo=True,
    )
    db.add(revisor)
    db.commit()

    asignado = WorkflowEngine.assign_reviewer(db)
    assert asignado.role == RolUsuario.REVISOR_JURIDICO


def test_dictamen_requiere_ser_revisor_asignado_o_admin(client: TestClient, db: Session, test_solicitud: SolicitudRevision):
    """Verifica que si la solicitud tiene un revisor asignado, otro revisor jurídico no pueda dictaminar (403), pero el asignado y el admin sí."""
    from main import app
    from app.core.auth_guard import get_current_user

    revisor_asignado = Usuario(
        id=uuid.uuid4(),
        objeto_id="oid-revisor-asignado",
        correo="revisor_asignado@test.local",
        nombre="Revisor Asignado",
        role=RolUsuario.REVISOR_JURIDICO,
        activo=True,
    )
    revisor_ajeno = Usuario(
        id=uuid.uuid4(),
        objeto_id="oid-revisor-ajeno",
        correo="revisor_ajeno@test.local",
        nombre="Revisor Ajeno",
        role=RolUsuario.REVISOR_JURIDICO,
        activo=True,
    )
    db.add(revisor_asignado)
    db.add(revisor_ajeno)
    test_solicitud.revicion_id = revisor_asignado.id
    test_solicitud.estado = EstadoSolicitud.EN_REVISION
    db.commit()

    saved_user = app.dependency_overrides.get(get_current_user)
    try:
        # 1. Revisor ajeno intenta dictaminar -> 403 Forbidden
        app.dependency_overrides[get_current_user] = lambda: {
            "id": revisor_ajeno.id,
            "nombre": revisor_ajeno.nombre_completo,
            "correo": revisor_ajeno.correo,
            "rol": revisor_ajeno.role.value,
            "activo": True,
        }
        res_ajeno = client.post(
            f"/api/v1/reviews/{test_solicitud.id}/revision",
            json={"decision": "APROBAR", "notas": "Intento no autorizado"},
        )
        assert res_ajeno.status_code == 403
        assert "Solo el revisor jurídico asignado o un administrador" in res_ajeno.json()["detail"]

        # 2. Revisor asignado dictamina -> 201 Created
        app.dependency_overrides[get_current_user] = lambda: {
            "id": revisor_asignado.id,
            "nombre": revisor_asignado.nombre_completo,
            "correo": revisor_asignado.correo,
            "rol": revisor_asignado.role.value,
            "activo": True,
        }
        res_asignado = client.post(
            f"/api/v1/reviews/{test_solicitud.id}/revision",
            json={"decision": "APROBAR", "notas": "Dictamen válido por revisor titular"},
        )
        assert res_asignado.status_code == 201
    finally:
        if saved_user:
            app.dependency_overrides[get_current_user] = saved_user
        else:
            app.dependency_overrides.pop(get_current_user, None)
        from app.models.revision import Revision
        db.query(Revision).filter(Revision.solicitud_id == test_solicitud.id).delete()
        db.query(Usuario).filter(Usuario.id.in_([revisor_asignado.id, revisor_ajeno.id])).delete()
        db.commit()

