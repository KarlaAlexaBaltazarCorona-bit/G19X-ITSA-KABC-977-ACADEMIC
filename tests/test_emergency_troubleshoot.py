"""Pruebas de verificación de los fixes de emergencia.

Cubre:
1. Panel de base de datos SQLAdmin (/admin -> 200)
2. CRUD completo de usuarios (/api/v1/usuarios/ -> list, create, update)
3. Guardado de revisión y transiciones de workflow sin error 500
4. Listado de revisiones (GET /api/v1/reviews/{id}/revision)
5. Dataset Power BI en formato HTML (/api/v1/analytics/powerbi-html)
6. Manejo seguro del chat con IA sin fallos 500
7. Rate Limiter ampliado y soporte de proxies (X-Forwarded-For)
"""

import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Documento
from app.models.solicitud import EstadoSolicitud, PrioridadSolicitud, SolicitudRevision
from app.models.user import RolUsuario, Usuario
from app.models.version import VersionDocumento


def test_sqladmin_panel_retorna_200(client: TestClient):
    """El panel de base de datos /admin debe estar disponible y responder 200."""
    res = client.get("/admin")
    assert res.status_code == 200
    assert "LegalTech" in res.text or "admin" in res.text.lower()


def test_crud_usuarios_admin(client: TestClient, db: Session):
    """El administrador puede listar, crear y actualizar usuarios sin 404."""
    # 1. Listar usuarios
    res_list = client.get("/api/v1/usuarios/")
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)

    # 2. Pre-registrar nuevo funcionario
    correo_prueba = f"abogado.{uuid.uuid4().hex[:6]}@plurione.com"
    payload_create = {
        "nombre": "Abogado Test",
        "apellido": "García",
        "correo": correo_prueba,
        "role": "REVISOR_JURIDICO",
    }
    user_id = None
    try:
        res_create = client.post("/api/v1/usuarios/", json=payload_create)
        assert res_create.status_code == 201
        user_data = res_create.json()
        user_id = user_data["id"]
        assert user_data["correo"] == correo_prueba
        assert user_data["role"] == "REVISOR_JURIDICO"
        assert user_data["activo"] is True

        # 3. Modificar rol y datos del usuario (PUT /api/v1/usuarios/{id})
        payload_update = {
            "nombre": "Abogado Promovido",
            "role": "APROBADOR_JURIDICO",
            "activo": True,
        }
        res_update = client.put(f"/api/v1/usuarios/{user_id}", json=payload_update)
        assert res_update.status_code == 200
        updated_data = res_update.json()
        assert updated_data["nombre"] == "Abogado Promovido"
        assert updated_data["role"] == "APROBADOR_JURIDICO"

        # 4. Desactivar usuario
        res_del = client.delete(f"/api/v1/usuarios/{user_id}")
        assert res_del.status_code == 200
        assert res_del.json()["activo"] is False
    finally:
        if user_id:
            db.query(Usuario).filter(Usuario.id == uuid.UUID(user_id)).delete()
            db.commit()


def test_guardar_revision_y_reglas_workflow(client: TestClient, db: Session):
    """Guardar revisión no debe fallar con 500 y debe ejecutar la transición de workflow."""
    # Crear usuario revisor y solicitante
    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    admin_user = db.query(Usuario).filter(Usuario.id == admin_id).first()
    if not admin_user:
        admin_user = Usuario(
            id=admin_id,
            objeto_id="admin-test",
            correo="admin@test.local",
            nombre="Admin",
            role=RolUsuario.ADMINISTRADOR_PLATAFORMA,
            activo=True,
        )
        db.add(admin_user)
        db.commit()

    # Crear solicitud en estado EN_REVISION
    sol = SolicitudRevision(
        titulo="Contrato de Prestación de Servicios 2026",
        requested_id=admin_id,
        revicion_id=admin_id,
        tipo_documento="contrato",
        prioridad=PrioridadSolicitud.NORMAL,
        estado=EstadoSolicitud.EN_REVISION,
    )
    db.add(sol)
    db.commit()
    db.refresh(sol)

    # Crear documento y versión
    doc = Documento(
        solicitud_id=sol.id,
        nombre="contrato_servicios.pdf",
        tipo_documento="contrato",
        creado_por=admin_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    ver = VersionDocumento(
        documento_id=doc.id,
        numero_version=1,
        nombre_archivo="contrato_servicios.pdf",
        ubicacion="test/contrato.pdf",
        tamano_archivo=1024,
        formato_archivo="application/pdf",
        actualizado_por=admin_id,
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)

    try:
        # 1. Registrar revisión con decisión APROBAR enviando documento_id
        payload_aprobar = {
            "documento_id": str(doc.id),
            "decision": "APROBAR",
            "notas": "Documento revisado conforme a normatividad vigente.",
        }
        res_rev = client.post(f"/api/v1/reviews/{sol.id}/revision", json=payload_aprobar)
        assert res_rev.status_code == 201
        rev_data = res_rev.json()
        assert rev_data["decision"] == "APROBAR"
        assert rev_data["vercion_documento_id"] == str(ver.id)

        # Verificar que el workflow avanzó a EN_APROBACION
        db.refresh(sol)
        assert sol.estado == EstadoSolicitud.EN_APROBACION

        # 2. Consultar historial de revisiones (GET /api/v1/reviews/{id}/revision)
        res_list_rev = client.get(f"/api/v1/reviews/{sol.id}/revision")
        assert res_list_rev.status_code == 200
        revs = res_list_rev.json()
        assert len(revs) >= 1
        assert revs[-1]["decision"] == "APROBAR"

        # 3. Registrar revisión con SOLICITAR_CAMBIOS -> pasa a OBSERVADO
        payload_cambios = {
            "decision": "SOLICITAR_CAMBIOS",
            "notas": "Se requiere ajustar cláusula de penalización.",
        }
        res_cambios = client.post(f"/api/v1/reviews/{sol.id}/revision", json=payload_cambios)
        assert res_cambios.status_code == 201
        db.refresh(sol)
        assert sol.estado == EstadoSolicitud.OBSERVADO
    finally:
        from app.models.revision import Revision
        db.query(Revision).filter(Revision.solicitud_id == sol.id).delete()
        db.query(VersionDocumento).filter(VersionDocumento.documento_id == doc.id).delete()
        db.query(Documento).filter(Documento.solicitud_id == sol.id).delete()
        db.query(SolicitudRevision).filter(SolicitudRevision.id == sol.id).delete()
        db.commit()


def test_powerbi_html_endpoint(client: TestClient):
    """El endpoint /powerbi-html debe retornar un documento HTML con una tabla para Power BI Web."""
    res = client.get("/api/v1/analytics/powerbi-html")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "<table" in res.text
    assert "Folio" in res.text
    assert "ID_Contrato" in res.text

    # El endpoint /powerbi-feed con format=html también debe retornar HTML
    res_feed_html = client.get("/api/v1/analytics/powerbi-feed?format=html")
    assert res_feed_html.status_code == 200
    assert "<table" in res_feed_html.text


def test_ai_chat_resilience(client: TestClient, db: Session):
    """El chat de IA por solicitud debe guardar mensajes y responder sin fallar en 500."""
    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    sol = SolicitudRevision(
        titulo="Convenio Marco de Colaboración",
        requested_id=admin_id,
        tipo_documento="convenio",
        prioridad=PrioridadSolicitud.NORMAL,
        estado=EstadoSolicitud.EN_REVISION,
    )
    db.add(sol)
    db.commit()
    db.refresh(sol)

    try:
        # Enviar mensaje al chat
        payload = {"pregunta": "¿Qué riesgos implica la cláusula de indemnización?"}
        res = client.post(f"/api/v1/ai/chat/{sol.id}", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["rol_mensaje"] == "asistente"
        assert len(data["contenido"]) > 0

        # Historial de chat
        res_hist = client.get(f"/api/v1/ai/chat/{sol.id}")
        assert res_hist.status_code == 200
        mensajes = res_hist.json()
        assert len(mensajes) >= 2
    finally:
        from app.models.extras import ChatMensaje
        db.query(ChatMensaje).filter(ChatMensaje.solicitud_id == sol.id).delete()
        db.query(SolicitudRevision).filter(SolicitudRevision.id == sol.id).delete()
        db.commit()


def test_rate_limiter_multiusuario_y_proxy():
    """El rate limiter debe identificar IPs distintas y usuarios independientes."""
    from starlette.requests import Request
    from app.core.rate_limiter import get_client_identifier

    # Caso 1: Usuario con Bearer token
    scope_auth = {
        "type": "http",
        "headers": [(b"authorization", b"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123")],
    }
    req_auth = Request(scope_auth)
    ident_auth = get_client_identifier(req_auth)
    assert ident_auth.startswith("user:")

    # Caso 2: Petición detrás de Azure proxy con X-Forwarded-For
    scope_proxy = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.195, 10.0.0.1")],
    }
    req_proxy = Request(scope_proxy)
    ident_proxy = get_client_identifier(req_proxy)
    assert ident_proxy == "203.0.113.195"

    # Caso 3: Colaborador con cabecera de sesión de navegador única (X-Client-Session-Id)
    scope_sess = {
        "type": "http",
        "headers": [(b"x-client-session-id", b"collab-tab-abc123xyz-session")],
    }
    req_sess = Request(scope_sess)
    ident_sess = get_client_identifier(req_sess)
    assert ident_sess == "sess:collab-tab-abc123xyz-session"


def test_extractor_texto_documento():
    """Valida la extracción de texto para archivos de texto plano, docx y pypdf."""
    from app.services.document_extractor import extract_text_from_bytes

    # Texto plano / markdown
    raw_texto = b"CONTRATO DE ARRENDAMIENTO\nClausula Primera: Objeto\nClausula Segunda: Renta mensual"
    res = extract_text_from_bytes(raw_texto, "contrato.txt", "text/plain")
    assert "CONTRATO DE ARRENDAMIENTO" in res
    assert "Clausula Primera" in res

    # Archivo vacío
    assert extract_text_from_bytes(b"", "vacio.pdf", "application/pdf") == ""

    # Imagen directa enrutada a OCR
    from unittest.mock import patch
    from app.services.azure_doc_intel import DocumentIntelligenceService

    with patch.object(DocumentIntelligenceService, "extract_clauses_from_pdf", return_value={"status": "ok", "texto": "TEXTO_OCR_IMAGEN"}):
        res_img = extract_text_from_bytes(b"fake_image_bytes", "contrato.png", "image/png")
        assert res_img == "TEXTO_OCR_IMAGEN"

    # PDF escaneado (sin texto digital o con texto insuficiente) enrutado a OCR
    with patch.object(DocumentIntelligenceService, "extract_clauses_from_pdf", return_value={"status": "ok", "texto": "TEXTO_OCR_ESCANEADO"}):
        res_scanned = extract_text_from_bytes(b"%PDF-1.4 dummy", "escaneado.pdf", "application/pdf")
        assert res_scanned == "TEXTO_OCR_ESCANEADO"


def test_azure_openai_429_backoff_retry(monkeypatch):
    """Valida que _create_completion reintente con backoff ante un error 429 RateLimit."""
    from unittest.mock import MagicMock
    from openai import RateLimitError
    import httpx
    from app.services.azure_openai import LegalAIService

    mock_client = MagicMock()
    # Simular que el primer intento da 429 y el segundo intento tiene éxito
    mock_resp_success = MagicMock()
    mock_resp_success.choices = [MagicMock(message=MagicMock(content="Dictamen contractual aprobado"))]

    error_429 = RateLimitError(
        message="Your requests to gpt-5-mini have exceeded token rate limit. Please retry after 1 seconds.",
        response=httpx.Response(status_code=429, request=httpx.Request("POST", "https://api.openai.com")),
        body={"error": {"message": "exceeded token rate limit"}},
    )

    mock_client.chat.completions.create.side_effect = [error_429, mock_resp_success]

    # No queremos esperar realmente en tests, mockear time.sleep
    monkeypatch.setattr("time.sleep", lambda s: None)

    res = LegalAIService._create_completion(
        client=mock_client,
        deployment_name="gpt-5-mini",
        messages=[{"role": "user", "content": "analiza el contrato"}],
        max_tokens=1000,
    )
    assert res == mock_resp_success
    assert mock_client.chat.completions.create.call_count == 2


def test_chat_con_texto_real_de_documento(client: TestClient, db: Session, monkeypatch):
    """El chat de IA debe recibir el texto real del documento en su contexto y permitir análisis."""
    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    sol = SolicitudRevision(
        titulo="Contrato de Confidencialidad y No Divulgacion 2026",
        requested_id=admin_id,
        tipo_documento="contrato",
        prioridad=PrioridadSolicitud.ALTA,
        estado=EstadoSolicitud.EN_REVISION,
    )
    db.add(sol)
    db.commit()
    db.refresh(sol)

    doc = Documento(
        solicitud_id=sol.id,
        nombre="nda_corporativo.txt",
        tipo_documento="contrato",
        creado_por=admin_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    texto_contrato = (
        "CONTRATO DE CONFIDENCIALIDAD (NDA)\n"
        "Partes: PluriOne Corp y Proveedor de Servicios TI.\n"
        "Clausula 1: Toda la informacion compartida es estrictamente confidencial por 5 anos.\n"
        "Clausula 2: La pena convencional por violacion es de $500,000 USD."
    )

    from app.services.document_extractor import cache_document_text
    cache_document_text(sol.id, texto_contrato)

    contexto_recibido = {}

    def mock_responder(historial, pregunta, contexto_documento=""):
        contexto_recibido["contexto"] = contexto_documento
        return "El documento es un NDA entre PluriOne y el Proveedor con vigencia de 5 años y pena de 500,000 USD."

    monkeypatch.setattr("app.services.azure_openai.LegalAIService.responder_con_contexto", mock_responder)

    try:
        payload = {"pregunta": "revisa el documento y dame generalidades del contenido"}
        res = client.post(f"/api/v1/ai/chat/{sol.id}", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "NDA" in data["contenido"]
        # Verificar que el contexto incluyó el texto real del contrato
        assert "pena convencional por violacion es de $500,000 USD" in contexto_recibido.get("contexto", "")
    finally:
        from app.models.extras import ChatMensaje
        db.query(ChatMensaje).filter(ChatMensaje.solicitud_id == sol.id).delete()
        db.query(Documento).filter(Documento.solicitud_id == sol.id).delete()
        db.query(SolicitudRevision).filter(SolicitudRevision.id == sol.id).delete()
        db.commit()

