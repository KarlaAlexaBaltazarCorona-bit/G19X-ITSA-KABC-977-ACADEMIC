-- ═════════════════════════════════════════════════════════════════════════════
-- Vistas SQL Optimizadas para Power BI — Plataforma LegalTech
-- Cumple con Requerimientos del Proyecto de Desarrollo (Sección 2: Power BI)
-- Base de Datos: Azure Database for PostgreSQL (Flexible Server: pg-proyecto-dev)
-- ═════════════════════════════════════════════════════════════════════════════

-- 1. Vista Principal de Solicitudes y Tiempos de Ciclo (Cycle Time & SLA)
CREATE OR REPLACE VIEW vw_powerbi_solicitudes_kpi AS
SELECT 
    s.id AS solicitud_id,
    COALESCE(s.numero_respuesta, 'SIN-FOLIO') AS folio_expediente,
    s.titulo AS titulo_documento,
    s.tipo_documento,
    s.prioridad,
    s.estado,
    -- Dimensiones del Solicitante
    u_sol.nombre || ' ' || COALESCE(u_sol.apellido, '') AS solicitante_nombre,
    u_sol.correo AS solicitante_correo,
    -- Dimensiones del Revisor
    COALESCE(u_rev.nombre || ' ' || COALESCE(u_rev.apellido, ''), 'Sin Asignar') AS revisor_nombre,
    u_rev.correo AS revisor_correo,
    -- Fechas del Workflow
    s.creado_at AS fecha_creacion,
    s.fecha_limite,
    s.finalizo_at AS fecha_finalizacion,
    -- Métricas de Tiempo Calculadas
    ROUND(
        EXTRACT(EPOCH FROM (COALESCE(s.finalizo_at, CURRENT_TIMESTAMP) - s.creado_at)) / 3600.0, 
        2
    ) AS duracion_horas,
    ROUND(
        EXTRACT(EPOCH FROM (COALESCE(s.finalizo_at, CURRENT_TIMESTAMP) - s.creado_at)) / 86400.0, 
        2
    ) AS duracion_dias,
    -- Indicador de Cumplimiento de SLA
    CASE 
        WHEN s.fecha_limite IS NULL THEN 'Sin SLA Definido'
        WHEN s.finalizo_at IS NOT NULL AND s.finalizo_at <= s.fecha_limite THEN 'Cumplido en Tiempo'
        WHEN s.finalizo_at IS NOT NULL AND s.finalizo_at > s.fecha_limite THEN 'Vencido Fuera de SLA'
        WHEN CURRENT_TIMESTAMP > s.fecha_limite AND s.estado NOT IN ('APROBADO', 'FIRMADO', 'RECHAZADO') THEN 'Vencido Activo'
        ELSE 'En Tiempo Activo'
    END AS estado_sla,
    CASE 
        WHEN s.fecha_limite IS NOT NULL AND COALESCE(s.finalizo_at, CURRENT_TIMESTAMP) <= s.fecha_limite THEN 1
        ELSE 0
    END AS es_cumplido_sla_binario
FROM solicitud_r s
LEFT JOIN users u_sol ON s.requested_id = u_sol.id
LEFT JOIN users u_rev ON s.revicion_id = u_rev.id;


-- 2. Vista de Detección de Cuellos de Botella por Revisor Legal
CREATE OR REPLACE VIEW vw_powerbi_cuellos_botella AS
SELECT 
    u.id AS revisor_id,
    u.nombre || ' ' || COALESCE(u.apellido, '') AS revisor_nombre,
    u.correo AS revisor_correo,
    COUNT(s.id) AS total_asignadas,
    SUM(CASE WHEN s.estado IN ('EN_REVISION', 'OBSERVADO') THEN 1 ELSE 0 END) AS pendientes_activas,
    SUM(CASE WHEN s.estado IN ('APROBADO', 'FIRMADO') THEN 1 ELSE 0 END) AS completadas_aprobadas,
    SUM(CASE WHEN s.estado = 'RECHAZADO' THEN 1 ELSE 0 END) AS completadas_rechazadas,
    ROUND(
        AVG(CASE 
            WHEN s.finalizo_at IS NOT NULL 
            THEN EXTRACT(EPOCH FROM (s.finalizo_at - s.creado_at)) / 3600.0 
            ELSE NULL 
        END), 
        1
    ) AS horas_promedio_resolucion
FROM users u
LEFT JOIN solicitud_r s ON s.revicion_id = u.id
WHERE u.role IN ('REVISOR_JURIDICO', 'APROBADOR_JURIDICO')
GROUP BY u.id, u.nombre, u.apellido, u.correo;


-- 3. Vista de Auditoría y Trazabilidad Cronológica de Eventos
CREATE OR REPLACE VIEW vw_powerbi_trazabilidad AS
SELECT 
    a.id AS auditoria_id,
    s.numero_respuesta AS folio_expediente,
    s.titulo AS documento_titulo,
    a.accion,
    a.estado_anterior,
    a.estado_nuevo,
    u.nombre || ' ' || COALESCE(u.apellido, '') AS usuario_actor,
    u.correo AS usuario_correo,
    a.ip_origen,
    a.creada_at AS timestamp_evento
FROM auditoria a
JOIN solicitud_r s ON a.solicitud_id = s.id
LEFT JOIN users u ON a.usuario_id = u.id
ORDER BY a.creada_at DESC;
