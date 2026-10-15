"""Pruebas de integración para el módulo de Solicitudes de Revisión.

No llaman a Postgres ni a Azure -- usan la BD SQLite en memoria y el usuario
de prueba definidos en `conftest.py`.
"""

from fastapi.testclient import TestClient


def test_listar_solicitudes_vacio(client: TestClient):
    """La lista de solicitudes empieza vacía en una BD limpia."""
    response = client.get("/api/v1/solicitudes/")
    assert response.status_code == 200
    assert response.json() == []


def test_crear_solicitud_sin_archivo_devuelve_422(client: TestClient):
    """Sin adjuntar un archivo, la creación de solicitud debe devolver error de validación."""
    response = client.post("/api/v1/solicitudes/", params={"titulo": "Contrato X", "tipo_documento": "contrato"})
    # 422 = Unprocessable Entity: falta el campo `archivo`
    assert response.status_code == 422


def test_solicitud_inexistente_devuelve_404(client: TestClient):
    """Pedir el detalle de un UUID inexistente debe devolver 404."""
    response = client.get("/api/v1/solicitudes/00000000-0000-0000-0000-999999999999")
    assert response.status_code == 404


def test_crear_solicitud_con_folio_y_prioridad(client: TestClient, db):
    """Crea una solicitud con archivo, prioridad y valida generación automática de folio EXP-YYYY-XXXX (HU-01, RF-002, RF-005)."""
    import io
    import uuid
    from app.models.user import RolUsuario, Usuario

    # Asegurar que exista un revisor activo para la asignación automática
    revisores_existentes = db.query(Usuario).filter(Usuario.role == RolUsuario.REVISOR_JURIDICO).all()
    if not revisores_existentes:
        revisor = Usuario(
            id=uuid.uuid4(),
            objeto_id="oid-revisor-hu01",
            nombre="Licenciado",
            apellido="Revisor",
            correo="revisor_hu01@test.local",
            role=RolUsuario.REVISOR_JURIDICO,
            activo=True,
        )
        db.add(revisor)
        db.commit()
        revisores_ids = [str(revisor.id)]
    else:
        revisores_ids = [str(r.id) for r in revisores_existentes]

    archivo_fake = ("contrato_arrendamiento.pdf", io.BytesIO(b"%PDF-1.4 Fake contract content"), "application/pdf")

    response = client.post(
        "/api/v1/solicitudes/",
        params={
            "titulo": "Contrato de Arrendamiento Planta Norte",
            "tipo_documento": "contrato",
            "descripcion": "Revisión urgente de cláusulas de fianza",
            "prioridad": "ALTA",
            "enviar_a_revision": "true",
        },
        files={"archivo": archivo_fake},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["titulo"] == "Contrato de Arrendamiento Planta Norte"
    assert data["prioridad"] == "ALTA"
    assert data["estado"] == "EN_REVISION"
    assert data["numero_respuesta"] is not None
    assert data["numero_respuesta"].startswith("EXP-")
    assert data["revicion_id"] in revisores_ids


def test_crear_solicitud_como_borrador_y_enviar_despues(client: TestClient, db):
    """Permite guardar en BORRADOR sin revisor y enviarlo a revisión posteriormente (HU-01, RF-003)."""
    import io
    import uuid
    from app.models.user import RolUsuario, Usuario

    # Revisor disponible
    revisor = db.query(Usuario).filter(Usuario.role == RolUsuario.REVISOR_JURIDICO).first()
    if not revisor:
        revisor = Usuario(
            id=uuid.uuid4(),
            objeto_id="oid-revisor-borrador",
            nombre="Abogado",
            apellido="Borrador",
            correo="revisor_borrador@test.local",
            role=RolUsuario.REVISOR_JURIDICO,
            activo=True,
        )
        db.add(revisor)
        db.commit()

    archivo_fake = ("politica_privacidad.docx", io.BytesIO(b"Fake Word Content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    # 1. Crear como borrador (enviar_a_revision=false)
    response = client.post(
        "/api/v1/solicitudes/",
        params={
            "titulo": "Política de Protección de Datos 2026",
            "tipo_documento": "politica",
            "prioridad": "NORMAL",
            "enviar_a_revision": "false",
        },
        files={"archivo": archivo_fake},
    )

    assert response.status_code == 201
    data = response.json()
    solicitud_id = data["id"]
    assert data["estado"] == "BORRADOR"
    assert data["revicion_id"] is None
    assert data["numero_respuesta"].startswith("EXP-")

    # 2. Despachar a revisión jurídica mediante endpoint /enviar
    resp_enviar = client.post(f"/api/v1/solicitudes/{solicitud_id}/enviar")
    assert resp_enviar.status_code == 200
    data_enviada = resp_enviar.json()
    assert data_enviada["estado"] == "EN_REVISION"
    assert data_enviada["revicion_id"] is not None

    # 3. Intentar enviar nuevamente una solicitud que ya está en revisión debe fallar 400
    resp_reintento = client.post(f"/api/v1/solicitudes/{solicitud_id}/enviar")
    assert resp_reintento.status_code == 400

