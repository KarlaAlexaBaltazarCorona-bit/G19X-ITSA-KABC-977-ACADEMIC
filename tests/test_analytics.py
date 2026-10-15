"""Pruebas unitarias y de integración para el módulo de Analítica y Power BI."""

import uuid
from datetime import datetime, UTC
from fastapi.testclient import TestClient

from app.models.solicitud import EstadoSolicitud, PrioridadSolicitud, SolicitudRevision
from app.models.user import RolUsuario, Usuario


def test_kpis_endpoint_empty_db(client: TestClient):
    """El endpoint de KPIs responde 200 y métricas en ceros con BD limpia."""
    response = client.get("/api/v1/analytics/kpis")
    assert response.status_code == 200
    data = response.json()
    assert data["total_solicitudes"] == 0
    assert data["tiempo_promedio_horas"] == 0.0
    assert data["tasa_cumplimiento_sla_pct"] == 100.0


def test_powerbi_feed_endpoint(client: TestClient):
    """El feed para Power BI responde 200 y una lista tabular vacía inicialmente."""
    response = client.get("/api/v1/analytics/powerbi-feed")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_bottlenecks_endpoint(client: TestClient):
    """El endpoint de detección de cuellos de botella responde con lista de revisores."""
    response = client.get("/api/v1/analytics/bottlenecks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_export_csv_endpoint(client: TestClient):
    """El endpoint de exportación CSV genera cabeceras de descarga de archivo."""
    response = client.get("/api/v1/analytics/export-csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "folio,titulo,tipo_documento" in response.text


def test_analytics_with_real_solicitudes(client: TestClient, db):
    """Verifica que el feed de Power BI y los KPIs calculen métricas con solicitudes reales."""
    usuario_test = Usuario(
        id=uuid.uuid4(),
        objeto_id="oid-analytics-user",
        nombre="Abogada",
        apellido="Corporativa",
        correo="abogada_bi@test.local",
        role=RolUsuario.REVISOR_JURIDICO,
        activo=True,
    )
    db.add(usuario_test)
    db.commit()

    solicitud = SolicitudRevision(
        id=uuid.uuid4(),
        numero_respuesta="EXP-2026-0099",
        titulo="Contrato Marco Power BI",
        tipo_documento="contrato",
        prioridad=PrioridadSolicitud.ALTA,
        estado=EstadoSolicitud.EN_REVISION,
        requested_id=usuario_test.id,
        revicion_id=usuario_test.id,
        creado_at=datetime.now(UTC),
    )
    db.add(solicitud)
    db.commit()

    try:
        # 1. Comprobar KPIs actualizados
        res_kpis = client.get("/api/v1/analytics/kpis")
        assert res_kpis.status_code == 200
        kpis = res_kpis.json()
        assert kpis["total_solicitudes"] >= 1
        assert kpis["en_revision"] >= 1

        # 2. Comprobar Feed de Power BI
        res_feed = client.get("/api/v1/analytics/powerbi-feed")
        assert res_feed.status_code == 200
        feed = res_feed.json()
        assert len(feed) >= 1
        item = next(x for x in feed if x["folio"] == "EXP-2026-0099")
        assert item["titulo"] == "Contrato Marco Power BI"
        assert item["tipo_documento"] == "contrato"
        assert item["prioridad"] == "ALTA"
        assert item["estado"] == "EN_REVISION"
        assert "Abogada" in item["revisor"]
    finally:
        db.delete(solicitud)
        db.delete(usuario_test)
        db.commit()
