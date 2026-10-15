"""Módulo de Analítica y Métricas para Power BI (HU-02, HU-12, HU-15, HU-16).

Proporciona fuentes de datos tabulares, agregaciones de KPIs y detección
de cuellos de botella para su consumo desde Power BI Desktop y Power BI Service.
"""

import csv
import io
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.solicitud import EstadoSolicitud, SolicitudRevision
from app.models.user import RolUsuario, Usuario

router = APIRouter()

ROLES_TODOS = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.AUDITOR.value,
)

ROLES_ANALITICA = (
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.AUDITOR.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.REVISOR_JURIDICO.value,
)


def _a_naive(dt: datetime | None) -> datetime | None:
    """Remueve tzinfo para comparaciones homogéneas entre SQLite y PostgreSQL."""
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def _calcular_horas(inicio: datetime | None, fin: datetime | None) -> float:
    """Calcula horas entre dos datetimes manejando de forma segura zonas horarias."""
    if not inicio:
        return 0.0
    if not fin:
        fin = datetime.now(UTC)
    t1 = _a_naive(inicio)
    t2 = _a_naive(fin)
    return round(abs((t2 - t1).total_seconds()) / 3600.0, 2) if t1 and t2 else 0.0


@router.get("/kpis", summary="Resumen ejecutivo de KPIs para tarjetas de Power BI")
def get_kpis(
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
) -> dict[str, Any]:
    """Calcula las métricas principales de rendimiento y gobernanza jurídica."""
    ahora = datetime.now(UTC)
    ahora_naive = _a_naive(ahora)
    solicitudes = db.query(SolicitudRevision).all()

    total = len(solicitudes)
    if total == 0:
        return {
            "total_solicitudes": 0,
            "en_revision": 0,
            "aprobadas": 0,
            "rechazadas": 0,
            "en_aprobacion": 0,
            "borradores": 0,
            "observadas": 0,
            "tiempo_promedio_horas": 0.0,
            "tasa_cumplimiento_sla_pct": 100.0,
            "solicitudes_vencidas": 0,
            "cuello_botella_principal": None,
        }

    estados = {
        "en_revision": sum(1 for s in solicitudes if s.estado == EstadoSolicitud.EN_REVISION),
        "aprobadas": sum(1 for s in solicitudes if s.estado in (EstadoSolicitud.APROBADO, EstadoSolicitud.FIRMADO)),
        "rechazadas": sum(1 for s in solicitudes if s.estado == EstadoSolicitud.RECHAZADO),
        "en_aprobacion": sum(1 for s in solicitudes if s.estado == EstadoSolicitud.EN_APROBACION),
        "borradores": sum(1 for s in solicitudes if s.estado == EstadoSolicitud.BORRADOR),
        "observadas": sum(1 for s in solicitudes if s.estado == EstadoSolicitud.OBSERVADO),
    }

    # Tiempos de ciclo en horas para solicitudes finalizadas
    tiempos_horas = []
    con_sla_cumplido = 0
    con_fecha_limite = 0
    vencidas = 0

    for s in solicitudes:
        if s.creado_at:
            horas = _calcular_horas(s.creado_at, s.finalizo_at or ahora)
            tiempos_horas.append(horas)

        if s.fecha_limite:
            con_fecha_limite += 1
            fl = _a_naive(s.fecha_limite)
            fn = _a_naive(s.finalizo_at)

            if fn and fl:
                if fn <= fl:
                    con_sla_cumplido += 1
            elif ahora_naive and fl and ahora_naive > fl and s.estado not in (EstadoSolicitud.APROBADO, EstadoSolicitud.FIRMADO, EstadoSolicitud.RECHAZADO):
                vencidas += 1
            else:
                con_sla_cumplido += 1

    tiempo_promedio = round(sum(tiempos_horas) / len(tiempos_horas), 1) if tiempos_horas else 0.0
    sla_pct = round((con_sla_cumplido / con_fecha_limite) * 100.0, 1) if con_fecha_limite > 0 else 100.0

    # Detección del principal cuello de botella (revisor con mayor número de solicitudes pendientes)
    pendientes_por_revisor = (
        db.query(Usuario.nombre, Usuario.apellido, func.count(SolicitudRevision.id))
        .join(SolicitudRevision, SolicitudRevision.revicion_id == Usuario.id)
        .filter(SolicitudRevision.estado == EstadoSolicitud.EN_REVISION)
        .group_by(Usuario.id, Usuario.nombre, Usuario.apellido)
        .order_by(func.count(SolicitudRevision.id).desc())
        .first()
    )

    cuello_botella = None
    if pendientes_por_revisor:
        nombre, apellido, cant = pendientes_por_revisor
        nombre_completo = f"{nombre} {apellido}".strip() if apellido else nombre
        cuello_botella = {"revisor": nombre_completo, "solicitudes_pendientes": cant}

    return {
        "total_solicitudes": total,
        **estados,
        "tiempo_promedio_horas": tiempo_promedio,
        "tasa_cumplimiento_sla_pct": sla_pct,
        "solicitudes_vencidas": vencidas,
        "cuello_botella_principal": cuello_botella,
    }


def render_powerbi_html_table(filas: list[dict[str, Any]]) -> str:
    """Genera un documento HTML con tabla estructurada optimizada para el motor de parsing de Power BI."""
    rows_html = []
    for f in filas:
        sla_text = "Sí" if f.get("cumple_sla") else "No"
        rows_html.append(
            f"<tr>"
            f"<td>{f.get('folio', '')}</td>"
            f"<td>{f.get('titulo', '')}</td>"
            f"<td>{f.get('tipo_documento', '')}</td>"
            f"<td>{f.get('prioridad', '')}</td>"
            f"<td>{f.get('estado', '')}</td>"
            f"<td>{f.get('solicitante', '')}</td>"
            f"<td>{f.get('revisor', '')}</td>"
            f"<td>{f.get('fecha_creacion') or ''}</td>"
            f"<td>{f.get('fecha_limite') or ''}</td>"
            f"<td>{f.get('fecha_finalizacion') or ''}</td>"
            f"<td>{f.get('duracion_horas', 0.0)}</td>"
            f"<td>{sla_text}</td>"
            f"<td>{f.get('total_revisiones', 0)}</td>"
            f"<td>{f.get('total_comentarios', 0)}</td>"
            f"<td>{f.get('id', '')}</td>"
            f"</tr>"
        )
    table_rows = "\n".join(rows_html)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Power BI Dataset - Workflow Jurídico PluriOne</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; margin: 2rem; background: #f8fafc; color: #1e293b; }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; color: #0f172a; }}
        p.desc {{ font-size: 0.88rem; color: #64748b; margin-top: 0; margin-bottom: 1.5rem; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; background: #e0e7ff; color: #3730a3; margin-bottom: 1rem; }}
        table {{ border-collapse: collapse; width: 100%; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        th {{ background: #0f172a; color: #ffffff; text-align: left; padding: 12px 14px; font-size: 0.82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
        td {{ padding: 10px 14px; font-size: 0.85rem; border-bottom: 1px solid #e2e8f0; color: #334155; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        tr:hover {{ background: #f1f5f9; }}
    </style>
</head>
<body>
    <h1>Dataset Corporativo de Flujo de Revisión Jurídica</h1>
    <p class="desc">Fuente de datos tabular estructurada en HTML para consumo automático desde Power BI (Conector Web).</p>
    <span class="badge">Registros totales: {len(filas)}</span>
    <table id="powerbi_contracts" border="1">
        <thead>
            <tr>
                <th>Folio</th>
                <th>Titulo</th>
                <th>Tipo_Documento</th>
                <th>Prioridad</th>
                <th>Estado</th>
                <th>Solicitante</th>
                <th>Revisor_Asignado</th>
                <th>Fecha_Creacion</th>
                <th>Fecha_Limite</th>
                <th>Fecha_Finalizacion</th>
                <th>Duracion_Horas</th>
                <th>Cumple_SLA</th>
                <th>Total_Revisiones</th>
                <th>Total_Comentarios</th>
                <th>ID_Contrato</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
</body>
</html>"""


@router.get("/powerbi-feed", summary="Dataset tabular estructurado para ingesta directa en Power BI")
def get_powerbi_feed(
    db: Session = Depends(get_db),
    request: Request = None,
    usuario: dict = Depends(requiere_roles(*ROLES_ANALITICA)),
):
    """Dataset plano desnormalizado optimizado para el conector Web de Power BI Desktop/Service."""
    solicitudes = db.query(SolicitudRevision).all()
    ahora = datetime.now(UTC)
    ahora_naive = _a_naive(ahora)
    filas = []

    for s in solicitudes:
        solicitante_nom = s.solicitante.nombre_completo if s.solicitante else "No asignado"
        revisor_nom = s.revisor.nombre_completo if s.revisor else "Sin asignar"

        duracion_horas = _calcular_horas(s.creado_at, s.finalizo_at or ahora)

        cumple_sla = True
        if s.fecha_limite:
            fl = _a_naive(s.fecha_limite)
            fn = _a_naive(s.finalizo_at)
            if fn and fl:
                cumple_sla = fn <= fl
            elif ahora_naive and fl:
                cumple_sla = ahora_naive <= fl

        filas.append({
            "id": str(s.id),
            "folio": s.numero_respuesta or "SIN-FOLIO",
            "titulo": s.titulo,
            "tipo_documento": s.tipo_documento,
            "prioridad": s.prioridad.value if hasattr(s.prioridad, "value") else str(s.prioridad),
            "estado": s.estado.value if hasattr(s.estado, "value") else str(s.estado),
            "solicitante": solicitante_nom,
            "revisor": revisor_nom,
            "fecha_creacion": s.creado_at.isoformat() if s.creado_at else None,
            "fecha_limite": s.fecha_limite.isoformat() if s.fecha_limite else None,
            "fecha_finalizacion": s.finalizo_at.isoformat() if s.finalizo_at else None,
            "duracion_horas": duracion_horas,
            "cumple_sla": cumple_sla,
            "total_revisiones": len(s.revisiones) if s.revisiones else 0,
            "total_comentarios": len(s.comentarios) if s.comentarios else 0,
        })

    # Si se solicita formato HTML explícito o se navega desde navegador / Power BI Web
    if request:
        format_param = request.query_params.get("format", "").lower()
        accept_header = request.headers.get("accept", "").lower()
        if format_param == "html" or ("text/html" in accept_header and "application/json" not in accept_header):
            return HTMLResponse(content=render_powerbi_html_table(filas))

    return filas


@router.get(
    "/powerbi-html",
    response_class=HTMLResponse,
    summary="Dataset tabular formateado en HTML para Conector Web de Power BI",
)
def get_powerbi_html(
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_ANALITICA)),
):
    """Genera una tabla HTML semántica estándar (<table>) directamente consumible
    por el conector 'Obtener Datos -> Desde la Web' de Power BI Desktop y Power BI Service,
    evitando la manipulación manual de JSON crudo o descarga manual de archivos CSV.
    """
    filas = get_powerbi_feed(request=None, db=db, usuario=usuario)
    return HTMLResponse(content=render_powerbi_html_table(filas))



@router.get("/bottlenecks", summary="Análisis de cuellos de botella por revisor legal")
def get_bottlenecks(
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_ANALITICA)),
) -> list[dict[str, Any]]:
    """Identifica la sobrecarga y tiempos de atención de cada abogado revisor."""
    revisores = db.query(Usuario).all()
    resultado = []

    for rev in revisores:
        asignadas = [s for s in rev.solicitudes_asignadas]
        if not asignadas:
            continue

        activas = [s for s in asignadas if s.estado in (EstadoSolicitud.EN_REVISION, EstadoSolicitud.OBSERVADO)]
        completadas = [s for s in asignadas if s.estado in (EstadoSolicitud.APROBADO, EstadoSolicitud.FIRMADO, EstadoSolicitud.RECHAZADO)]

        resultado.append({
            "revisor_id": str(rev.id),
            "revisor_nombre": rev.nombre_completo,
            "revisor_correo": rev.correo,
            "solicitudes_totales": len(asignadas),
            "pendientes_activas": len(activas),
            "completadas": len(completadas),
            "indice_carga": len(activas),
        })

    # Ordenar por el que tiene mayor carga activa (cuello de botella primero)
    resultado.sort(key=lambda x: x["pendientes_activas"], reverse=True)
    return resultado


@router.get("/export-csv", summary="Descarga directa de datos en CSV para Power BI Desktop")
def export_csv(
    db: Session = Depends(get_db),
    usuario: dict = Depends(requiere_roles(*ROLES_ANALITICA)),
) -> Response:
    """Genera y descarga un archivo CSV con las métricas para importación directa en Power BI o Excel."""
    datos = get_powerbi_feed(db)
    output = io.StringIO()

    campos = [
        "id", "folio", "titulo", "tipo_documento", "prioridad", "estado",
        "solicitante", "revisor", "fecha_creacion", "fecha_limite",
        "fecha_finalizacion", "duracion_horas", "cumple_sla",
        "total_revisiones", "total_comentarios"
    ]

    writer = csv.DictWriter(output, fieldnames=campos)
    writer.writeheader()
    for fila in datos:
        writer.writerow(fila)

    contenido_csv = output.getvalue()
    return Response(
        content=contenido_csv,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="powerbi_legaltech_metrics.csv"'},
    )
