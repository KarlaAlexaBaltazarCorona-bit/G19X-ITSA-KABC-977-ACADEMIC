# 📊 Integración de Power BI — Plataforma LegalTech

Este directorio contiene la arquitectura, vistas SQL y medidas DAX para conectar **Power BI Desktop** y **Power BI Service** con la plataforma de workflow jurídico, cumpliendo con la especificación técnica del **Proyecto de Desarrollo (Sección 2: Power BI)** y las historias de usuario **HU-02**, **HU-12**, **HU-15** y **HU-16**.

---

## 🏗️ 1. Arquitectura de Datos para Power BI

La plataforma ofrece **dos métodos de conexión** independientes:

```
┌─────────────────────────────────┐
│     Power BI Desktop / Web      │
└───────────────┬─────────────────┘
                │
     ┌──────────┴──────────┐
     ▼                     ▼
[ Método A: SQL Directo ] [ Método B: REST API Feed ]
Azure PostgreSQL Flexible  FastAPI Endpoint
pg-proyecto-dev            /api/v1/analytics/powerbi-feed
(Vistas SQL Optimizadas)  (JSON Tabular / Export CSV)
```

---

## 🚀 2. Métodos de Conexión en Power BI Desktop

### Método A: Conexión Nativa a Azure PostgreSQL (Recomendado para Informes en Vivo)
1. Abre **Power BI Desktop**.
2. Clic en **Obtener datos (Get Data)** -> **Más...** -> **Base de datos de PostgreSQL**.
3. Ingresa los parámetros de conexión de Azure:
   * **Servidor:** `pg-proyecto-dev.postgres.database.azure.com:5432`
   * **Base de datos:** `legaltech_db` (o el nombre configurado en tu servidor).
   * **Modo de conectividad:** `Importar` o `DirectQuery`.
4. En autenticación, selecciona **Base de datos** e introduce tu usuario y contraseña.
5. Selecciona las vistas pre-creadas:
   * `vw_powerbi_solicitudes_kpi` (Tabla principal de hechos y dimensiones).
   * `vw_powerbi_cuellos_botella` (Dimensión de revisores y análisis de carga).
   * `vw_powerbi_trazabilidad` (Registro histórico para auditoría forense).

### Método B: Conexión Web REST API (Sin Credenciales de Base de Datos)
1. En Power BI Desktop, clic en **Obtener datos** -> **Web**.
2. Selecciona **Básico** e introduce la URL del endpoint:
   ```
   https://legaltech-api-LegalprojectIA-1134.azurewebsites.net/api/v1/analytics/powerbi-feed
   ```
   *(O localmente: `http://localhost:8000/api/v1/analytics/powerbi-feed`)*
3. En la cabecera HTTP de solicitud agrega:
   * `X-API-KEY`: `[TU_APP_API_KEY]`
4. Power BI importará la tabla JSON automáticamente y podrás hacer clic en **Cerrar y aplicar**.

---

## 📐 3. Medidas DAX Predefinidas para el Informe

Copia y pega estas fórmulas DAX en tu informe de Power BI:

### A. Tiempo Promedio de Resolución (Turnaround Time - TAT)
```dax
Tiempo Promedio Revision (Horas) = 
AVERAGE(vw_powerbi_solicitudes_kpi[duracion_horas])
```

### B. Porcentaje de Cumplimiento de SLA (KPI Principal de Eficiencia)
```dax
% Cumplimiento SLA = 
DIVIDE(
    CALCULATE(COUNTROWS(vw_powerbi_solicitudes_kpi), vw_powerbi_solicitudes_kpi[es_cumplido_sla_binario] = 1),
    COUNTROWS(vw_powerbi_solicitudes_kpi),
    1
) * 100
```

### C. Detección de Cuellos de Botella (Backlog Activo por Abogado)
```dax
Solicitudes Pendientes Activas = 
CALCULATE(
    COUNTROWS(vw_powerbi_solicitudes_kpi),
    vw_powerbi_solicitudes_kpi[estado] IN {"EN_REVISION", "OBSERVADO"}
)
```

### D. Tasa de Aprobación Jurídica
```dax
% Aprobacion = 
DIVIDE(
    CALCULATE(COUNTROWS(vw_powerbi_solicitudes_kpi), vw_powerbi_solicitudes_kpi[estado] IN {"APROBADO", "FIRMADO"}),
    CALCULATE(COUNTROWS(vw_powerbi_solicitudes_kpi), vw_powerbi_solicitudes_kpi[estado] IN {"APROBADO", "FIRMADO", "RECHAZADO"}),
    0
) * 100
```

---

## 📊 4. Estructura de Visualizaciones Sugerida (Dashboard Ejecutivo)

| Panel Visual | Tipo de Gráfico | Campos Utilizados |
| :--- | :--- | :--- |
| **Tarjetas KPI Superiores** | Tarjeta de número único | `Total Solicitudes`, `% Cumplimiento SLA`, `Tiempo Promedio (Horas)`, `Solicitudes Vencidas` |
| **Cuellos de Botella por Revisor** | Gráfico de barras horizontales | Eje Y: `revisor_nombre` \| Eje X: `Solicitudes Pendientes Activas` |
| **Embudo de Estados del Workflow** | Gráfico de embudo (Funnel) | Fases: `Borrador` -> `En Revisión` -> `En Aprobación` -> `Aprobado / Firmado` |
| **Distribución por Tipo y Riesgo** | Gráfico de Donut / Anillo | Leyenda: `tipo_documento` (Contrato, Convenio, Política) |
| **Tendencia de Solicitudes en el Tiempo** | Gráfico de líneas y áreas | Eje X: `fecha_creacion` (Mes/Semana) \| Eje Y: Recuento de solicitudes |

---

## 📖 5. Documentación Relacionada

- [🧭 Centro de Documentación Oficial](../docs/INDEX.md)
- [🏛️ Arquitectura del Sistema](../docs/ARQUITECTURA_SISTEMA.md)
- [📘 Manual de Usuario y Roles](../docs/MANUAL_USUARIO_Y_ROLES.md)
- [📡 Referencia de la API RESTful (Endpoints de Analítica)](../docs/API_REFERENCE.md#-9-módulo-de-analítica-y-power-bi-analytics)

