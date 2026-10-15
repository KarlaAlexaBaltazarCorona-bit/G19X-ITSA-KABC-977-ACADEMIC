# 📡 Referencia de la API RESTful (v1) — LegalprojectIA

**Prefijo Base:** `/api/v1`  
**Formato de Intercambio:** `application/json` (o `multipart/form-data` para subida de documentos)  
**Especificación OpenAPI:** `/docs` (Swagger UI en entorno local) y `/openapi.json`  

---

## 📑 Tabla de Contenidos
1. [Esquema de Autenticación y Cabeceras Requeridas](#-1-esquema-de-autenticación-y-cabeceras-requeridas)
2. [Módulo de Autenticación (`/auth`)](#-2-módulo-de-autenticación-auth)
3. [Módulo de Solicitudes y Expedientes (`/solicitudes`)](#-3-módulo-de-solicitudes-y-expedientes-solicitudes)
4. [Módulo de Workflows y Bandeja de Tareas (`/workflows`)](#-4-módulo-de-workflows-y-bandeja-de-tareas-workflows)
5. [Módulo de Gestión Documental y Versiones (`/documents`)](#-5-módulo-de-gestión-documental-y-versiones-documents)
6. [Módulo de Revisiones y Comentarios (`/reviews`)](#-6-módulo-de-revisiones-y-comentarios-reviews)
7. [Módulo de Dictámenes y Firmas Electrónicas (`/signatures`)](#-7-módulo-de-dictámenes-y-firmas-electrónicas-signatures)
8. [Módulo de Inteligencia Artificial Jurídica (`/ai`)](#-8-módulo-de-inteligencia-artificial-jurídica-ai)
9. [Módulo de Analítica y Power BI (`/analytics`)](#-9-módulo-de-analítica-y-power-bi-analytics)
10. [Módulo de Auditoría y Trazabilidad (`/audit`)](#-10-módulo-de-auditoría-y-trazabilidad-audit)
11. [Módulo de Notificaciones y SLA (`/notifications`)](#-11-módulo-de-notificaciones-y-sla-notifications)
12. [Módulo de Usuarios y Roles (`/usuarios`)](#-12-módulo-de-usuarios-y-roles-usuarios)
13. [Códigos de Estado HTTP y Manejo de Errores](#-13-códigos-de-estado-http-y-manejo-de-errores)

---

## 🔒 1. Esquema de Autenticación y Cabeceras Requeridas

Todos los endpoints protegidos bajo `/api/v1/...` requieren dos niveles de control:

1. **Cabecera de Clave de API Corporativa (`X-API-KEY`):**
   - Protege los endpoints contra escaneos no autorizados en internet (CWE-200).
   - Cabecera: `X-API-KEY: [APP_API_KEY]`
2. **Token de Identidad Microsoft Entra ID (`Authorization`):**
   - Token JWT Bearer obtenido tras el flujo de inicio de sesión con Microsoft 365.
   - Cabecera: `Authorization: Bearer <ID_TOKEN_O_ACCESS_TOKEN>`
   - Opcionalmente proporcionado vía cookie HTTP segura `plurione_auth_token` para peticiones originadas desde el navegador web.

---

## 🔑 2. Módulo de Autenticación (`/auth`)

### `GET /api/v1/auth/config`
Retorna los identificadores públicos requeridos por la librería cliente MSAL.js para inicializar el inicio de sesión.
- **Seguridad:** Público (sin credenciales).
- **Respuesta (200 OK):**
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "authority": "https://login.microsoftonline.com/common",
  "redirectUri": "https://legaltech-api-LegalprojectIA-1134.azurewebsites.net/login"
}
```

### `GET /api/v1/auth/me`
Obtiene los datos del perfil y rol asignado al usuario actualmente autenticado.
- **Seguridad:** Requiere Bearer Token.
- **Respuesta (200 OK):**
```json
{
  "id": 1,
  "email": "abogado.revisor@empresa.com",
  "nombre_completo": "Lic. Roberto Gómez",
  "rol": "REVISOR_JURIDICO",
  "activo": true
}
```

### `POST /api/v1/auth/logout`
Cierra la sesión del usuario, invalidando las cookies seguras.

---

## 📋 3. Módulo de Solicitudes y Expedientes (`/solicitudes`)

### `GET /api/v1/solicitudes/`
Lista todas las solicitudes registradas, permitiendo filtros por estado, prioridad o texto.
- **Roles:** Todos los usuarios autenticados.
- **Query Params:** `skip` (int, default 0), `limit` (int, default 50), `estado` (string opcional).

### `POST /api/v1/solicitudes/`
Crea un nuevo expediente legal con su archivo adjunto primario.
- **Roles:** `REVISOR_JURIDICO`, `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.
- **Content-Type:** `multipart/form-data`
- **Parámetros Form:**
  - `titulo` (string, obligatorio)
  - `tipo_documento` (string, obligatorio: ej. `CONTRATO_MERCANTIL`, `NDA`, etc.)
  - `prioridad` (string: `BAJA`, `MEDIA`, `ALTA`, `URGENTE`)
  - `descripcion` (string, opcional)
  - `es_borrador` (bool, default `false`)
  - `file` (UploadFile, obligatorio: PDF o DOCX)
- **Respuesta (201 Created):**
```json
{
  "id": 15,
  "folio": "EXP-2026-0015",
  "titulo": "Contrato de Servicios Tecnológicos",
  "estado": "EN_REVISION",
  "abogado_asignado_id": 4,
  "fecha_creacion": "2026-10-01T15:30:00Z"
}
```

### `GET /api/v1/solicitudes/{id}`
Obtiene el detalle íntegro de un expediente, incluyendo su documento principal, versión actual y abogado asignado.

### `POST /api/v1/solicitudes/{id}/decision`
Registra la decisión formal del aprobador jurídico.
- **Roles:** `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.
- **Cuerpo JSON:**
```json
{
  "decision": "APROBADO",
  "observaciones": "Cumple con las directrices legales internas."
}
```

---

## 📥 4. Módulo de Workflows y Bandeja de Tareas (`/workflows`)

### `GET /api/v1/workflows/inbox`
Recupera el listado de expedientes pendientes de atención del usuario en sesión.
- **Roles:** `REVISOR_JURIDICO`, `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.
- **Respuesta (200 OK):**
```json
[
  {
    "solicitud_id": 15,
    "folio": "EXP-2026-0015",
    "titulo": "Contrato de Suministro",
    "etapa_actual": "EN_REVISION",
    "prioridad": "ALTA",
    "sla_horas_restantes": 18.5,
    "sla_vencido": false
  }
]
```

---

## 📁 5. Módulo de Gestión Documental y Versiones (`/documents`)

### `POST /api/v1/documents/{solicitud_id}/version`
Carga una nueva versión de un documento observado previamente.
- **Content-Type:** `multipart/form-data`
- **Parámetros:** `file` (UploadFile), `descripcion_cambios` (string).
- **Proceso:** Calcula el resumen criptográfico SHA-256, almacena en Azure Blob Storage, crea el registro `VersionDocumento` y actualiza el puntero a la versión activa.

### `GET /api/v1/documents/{solicitud_id}/versions`
Retorna el historial completo de versiones de la solicitud con sus hashes y URLs seguras.

---

## 💬 6. Módulo de Revisiones y Comentarios (`/reviews`)

### `POST /api/v1/reviews/`
Registra el dictamen técnico del abogado revisor.
- **Roles:** `REVISOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.
- **Cuerpo JSON:**
```json
{
  "solicitud_id": 15,
  "resultado": "APROBADO_CON_OBSERVACIONES",
  "dictamen_texto": "Se sugiere modificar la cláusula de penalización por mora."
}
```

### `POST /api/v1/reviews/comments`
Agrega un comentario al expediente o responde a un hilo existente.
- **Cuerpo JSON:**
```json
{
  "solicitud_id": 15,
  "parent_id": null,
  "contenido": "Favor de revisar la vigencia estipulada en el punto 3.2."
}
```

---

## ✍️ 7. Módulo de Dictámenes y Firmas Electrónicas (`/signatures`)

### `POST /api/v1/signatures/sign`
Estampa la firma electrónica con valor probatorio sobre un documento formalmente aprobado.
- **Roles:** `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.
- **Cuerpo JSON:**
```json
{
  "solicitud_id": 15,
  "declaracion_conformidad": "Acepto los términos del contrato en mi carácter de Director Jurídico."
}
```
- **Respuesta (200 OK):**
```json
{
  "firma_id": 8,
  "solicitud_id": 15,
  "firma_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "fecha_firma": "2026-10-01T15:45:00Z",
  "firmante": "Lic. Roberto Gómez"
}
```

---

## 🧠 8. Módulo de Inteligencia Artificial Jurídica (`/ai`)

### `POST /api/v1/ai/query`
Realiza consultas en lenguaje natural sobre el contenido del documento del expediente.
- **Cuerpo JSON:**
```json
{
  "solicitud_id": 15,
  "prompt": "¿Cuáles son las obligaciones del proveedor en caso de incumplimiento de entrega?"
}
```
- **Respuesta (200 OK):**
```json
{
  "solicitud_id": 15,
  "respuesta": "Conforme a la Cláusula Octava (Pena Convencional), el proveedor deberá pagar el 1.5% diario del valor total por cada día hábil de retraso...",
  "fuente": "Texto original del documento (Página 4, Párrafo 2)"
}
```

### `POST /api/v1/ai/risks`
Ejecuta el análisis automatizado de riesgos jurídicos sobre el contrato.
- **Retorno:** Lista priorizada de cláusulas de riesgo alto, medio y bajo con justificación normativa.

### `POST /api/v1/ai/summary`
Genera un resumen ejecutivo de las partes, objeto, vigencia, montos y jurisdicción aplicable.

---

## 📊 9. Módulo de Analítica y Power BI (`/analytics`)

### `GET /api/v1/analytics/kpis`
Retorna métricas consolidadas en tiempo real:
- Total solicitudes, tiempo promedio de resolución (horas), % cumplimiento SLA, tasa de aprobación.

### `GET /api/v1/analytics/powerbi-feed`
Endpoint tabular optimizado para consumo directo de Microsoft Power BI Desktop y Service.
- **Roles:** `AUDITOR`, `ADMINISTRADOR_PLATAFORMA`.
- **Retorno:** Arreglo JSON con todas las dimensiones y hechos de expedientes, revisores y tiempos.

### `GET /api/v1/analytics/bottlenecks`
Analiza la distribución de carga y tiempos muertos para identificar revisores saturados o etapas lentas.

### `GET /api/v1/analytics/export/csv`
Descarga de archivo CSV plano con los datos del flujo para análisis externo.

---

## 🕵️‍♂️ 10. Módulo de Auditoría y Trazabilidad (`/audit`)

### `GET /api/v1/audit/`
Consulta la bitácora inmutable de eventos del sistema.
- **Roles:** `AUDITOR`, `ADMINISTRADOR_PLATAFORMA`.
- **Query Params:** `skip`, `limit`, `usuario_id`, `accion`, `fecha_inicio`, `fecha_fin`.
- **Respuesta (200 OK):**
```json
[
  {
    "id": 142,
    "usuario_email": "abogado@empresa.com",
    "rol": "REVISOR_JURIDICO",
    "accion": "DICTAMEN_EMITIDO",
    "entidad": "SolicitudRevision #15",
    "ip_origen": "187.190.22.10",
    "timestamp": "2026-10-01T15:40:12Z"
  }
]
```

---

## 🔔 11. Módulo de Notificaciones y SLA (`/notifications`)

### `GET /api/v1/notifications/`
Recupera las notificaciones no leídas del usuario en sesión.

### `PUT /api/v1/notifications/{id}/read`
Marca una notificación como leída.

---

## 👥 12. Módulo de Usuarios y Roles (`/usuarios`)

### `GET /api/v1/usuarios/`
Lista los colaboradores registrados en el sistema.
- **Roles:** `ADMINISTRADOR_PLATAFORMA`.

### `PUT /api/v1/usuarios/{id}/rol`
Actualiza el perfil o estatus de activación de un usuario.
- **Cuerpo JSON:**
```json
{
  "rol": "APROBADOR_JURIDICO",
  "activo": true
}
```

---

## 🚨 13. Códigos de Estado HTTP y Manejo de Errores

| Código | Significado | Causa Habitual |
| :---: | :--- | :--- |
| **200** | OK | Operación exitosa. |
| **201** | Created | Recurso creado correctamente en el sistema. |
| **400** | Bad Request | Parámetros inválidos o formato no soportado. |
| **401** | Unauthorized | Token Bearer faltante, expirado o firma inválida. |
| **403** | Forbidden | El rol del usuario no tiene privilegios para este endpoint. |
| **404** | Not Found | El folio, expediente o archivo solicitado no existe. |
| **413** | Payload Too Large | El archivo subido excede el límite de 20 MB. |
| **422** | Unprocessable Entity | Error en la validación de esquemas Pydantic. |
| **429** | Too Many Requests | Se superó el límite de peticiones permitido por minuto. |
| **500** | Internal Server Error | Error no controlado (retorna código opaco de rastreo). |
