# 👥 Manual de Usuario y Guía de Roles — LegalprojectIA
## Plataforma de Workflow para Revisión Jurídica Asistida por Inteligencia Artificial

---

## 📑 Tabla de Contenidos
1. [Introducción y Objetivos](#-1-introducción-y-objetivos)
2. [Estructura de Roles y Responsabilidades (RBAC)](#-2-estructura-de-roles-y-responsabilidades-rbac)
3. [Inicio de Sesión Institucional (Microsoft Entra ID)](#-3-inicio-de-sesión-institucional-microsoft-entra-id)
4. [Módulo 1: Dashboard y Navegación General](#-4-módulo-1-dashboard-y-navegación-general)
5. [Módulo 2: Creación de Solicitudes y Carga de Contratos](#-5-módulo-2-creación-de-solicitudes-y-carga-de-contratos)
6. [Módulo 3: Bandeja de Trabajo y Asignación de Tareas](#-6-módulo-3-bandeja-de-trabajo-y-asignación-de-tareas)
7. [Módulo 4: Mesa de Revisión Jurídica y Asistente IA](#-7-módulo-4-mesa-de-revisión-jurídica-y-asistente-ia)
8. [Módulo 5: Hilos de Comentarios y Observaciones](#-8-módulo-5-hilos-de-comentarios-y-observaciones)
9. [Módulo 6: Control de Versiones e Inmutabilidad](#-9-módulo-6-control-de-versiones-e-inmutabilidad)
10. [Módulo 7: Dictamen y Aprobación Formal](#-10-módulo-7-dictamen-y-aprobación-formal)
11. [Módulo 8: Registro de Firma Electrónica Criptográfica](#-11-módulo-8-registro-de-firma-electrónica-criptográfica)
12. [Módulo 9: Bitácora de Auditoría y Trazabilidad Forense](#-12-módulo-9-bitácora-de-auditoría-y-trazabilidad-forense)
13. [Módulo 10: Panel de Administración y Gestión de Usuarios](#-13-módulo-10-panel-de-administración-y-gestión-de-usuarios)
14. [Módulo 11: Tableros Analíticos en Power BI](#-14-módulo-11-tableros-analíticos-en-power-bi)

---

## 📖 1. Introducción y Objetivos

Este manual tiene como propósito guiar a los colaboradores, abogados dictaminadores, directores jurídicos, auditores y administradores de sistemas en la operación cotidiana de la plataforma **LegalprojectIA**.

El sistema optimiza el tiempo de respuesta en la formalización de documentos legales, reduce riesgos contractuales mediante análisis asistido por Inteligencia Artificial y garantiza el apego regulatorio a través de una pista de auditoría inmutable.

---

## 🎖️ 2. Estructura de Roles y Responsabilidades (RBAC)

La plataforma cuenta con **cuatro perfiles oficiales**, alineados a la jerarquía de gobierno corporativo:

```
┌─────────────────────────────────────────────────────────────┐
│                 ADMINISTRADOR_PLATAFORMA                    │
│   (Supervisa sistema, gestiona usuarios y configuración)    │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
┌──────────────▼──────────────┐ ┌──────────────▼──────────────┐
│     APROBADOR_JURIDICO      │ │           AUDITOR           │
│ (Autoriza dictámenes finales│ │ (Monitorea trazabilidad, SLA│
│     y ejecuta firmas)       │ │     y bitácora forense)     │
└──────────────┬──────────────┘ └─────────────────────────────┘
               │
┌──────────────▼──────────────┐
│       REVISOR_JURIDICO      │
│ (Analiza contratos con IA,  │
│  comenta y emite dictamen)  │
└─────────────────────────────┘
```

### Resumen de Atribuciones por Rol:

1. **Revisor Jurídico (`REVISOR_JURIDICO`):**
   - Atiende las solicitudes que le son asignadas automáticamente por balanceo de carga.
   - Analiza el contenido de los documentos utilizando el Asistente de IA (Azure OpenAI).
   - Redacta comentarios, observaciones y solicita correcciones.
   - Emite el dictamen preliminar (Aceptable / Observado).

2. **Aprobador Jurídico (`APROBADOR_JURIDICO`):**
   - Revisa las solicitudes validadas por los revisores.
   - Toma la decisión formal de negocio: **Aprobar** o **Rechazar**.
   - Aplica la firma electrónica sellada criptográficamente sobre el documento final.

3. **Auditor (`AUDITOR`):**
   - Acceso de solo lectura a la bitácora completa de eventos del sistema (`/api/v1/app/trazabilidad`).
   - Monitorea el cumplimiento de SLAs, tiempos de atención por abogado y descargas de documentos.
   - Consulta los tableros analíticos en Power BI.

4. **Administrador de la Plataforma (`ADMINISTRADOR_PLATAFORMA`):**
   - Control total de la plataforma.
   - Da de alta nuevos colaboradores y modifica sus roles (`/api/v1/app/usuarios`).
   - Accede al panel ORM directo (`/admin`) para labores de mantenimiento y soporte de datos.
   - Supervisa métricas globales de salud del sistema y volumen transaccional.

---

## 🔑 3. Inicio de Sesión Institucional (Microsoft Entra ID)

La plataforma utiliza el protocolo seguro OpenID Connect / OAuth2 a través de **Microsoft Entra ID**:

1. Ingrese a la URL de la plataforma:
   - **Producción:** `https://app-legaltech-z5m4thvbo3byk.azurewebsites.net/login`
   - **Local:** `http://localhost:8000/login`
2. Haga clic en el botón corporativo **"Iniciar Sesión con Microsoft 365"**.
3. Se abrirá la ventana oficial de autenticación de Microsoft:
   - Ingrese su correo institucional (ej. `abogado@empresa.com` o cuenta autorizada).
   - Ingrese su contraseña y complete el factor de autenticación multifactor (MFA) si está configurado en su organización.
4. Al autenticarse satisfactoriamente, el sistema recuperará su identidad, asignará sus permisos correspondientes y lo redirigirá al **Dashboard Principal**.

> 💡 **Nota de Seguridad:** La sesión almacena un token JWT firmado criptográficamente en el navegador. Al cerrar la pestaña o hacer clic en **"Cerrar Sesión"**, el token es revocado y las cookies seguras son eliminadas.

---

## 📊 4. Módulo 1: Dashboard y Navegación General

**Ruta:** `/api/v1/app/dashboard`  
**Roles:** Todos los usuarios autenticados.

El Dashboard ofrece una panorámica instantánea de la carga de trabajo:
- **Tarjetas Resumen:** Total de solicitudes creadas, pendientes de atención, solicitudes observadas y expedientes finalizados/firmados.
- **Acceso Rápido:** Botones directos a "Nueva Solicitud" y "Mis Tareas Pendientes".
- **Listado Reciente:** Tabla interactiva con los últimos expedientes gestionados, mostrando su folio único, título, prioridad y estado actual.
- **Menú Lateral:** Navegación contextual adaptada automáticamente según el rol del usuario en sesión.

---

## 📝 5. Módulo 2: Creación de Solicitudes y Carga de Contratos

**Ruta:** `/api/v1/app/nueva`  
**Roles:** `REVISOR_JURIDICO`, `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.

Para registrar un nuevo expediente para revisión jurídica:

1. Haga clic en **"Nueva Solicitud"** en el menú lateral.
2. Complete el formulario con los siguientes campos:
   - **Título del Asunto:** Nombre descriptivo (ej. *"Contrato de Prestación de Servicios Tecnológicos 2026"*).
   - **Tipo de Documento:** Seleccione entre *Contrato Mercantil*, *Convenio de Confidencialidad (NDA)*, *Adenda Contractual*, *Poder Notarial*, o *Otro*.
   - **Prioridad:** *Baja*, *Media*, *Alta*, o *Urgente*. (Afecta el cálculo del plazo límite de SLA).
   - **Descripción / Observaciones Iniciales:** Notas contextuales o instrucciones específicas para el abogado revisor.
   - **Archivo Adjunto:** Seleccione el documento en formato `.pdf` o `.docx` (tamaño máximo permitido: 20 MB).
3. Seleccione el modo de guardado:
   - **Guardar como Borrador:** Permite almacenar la solicitud sin que sea turnada a un revisor todavía.
   - **Enviar a Revisión:** Asigna automáticamente un folio único (ej. `EXP-2026-0042`), sube el archivo a Azure Blob Storage, extrae el hash SHA-256 e inicia el balanceo de carga para asignar al abogado revisor más desocupado.

---

## 📥 6. Módulo 3: Bandeja de Trabajo y Asignación de Tareas

**Ruta:** `/api/v1/app/tareas`  
**Roles:** `REVISOR_JURIDICO`, `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.

La bandeja de trabajo muestra exclusivamente las tareas que requieren la intervención activa del usuario en sesión:
- **Pestaña "Mis Pendientes":** Solicitudes asignadas al usuario en estado `EN_REVISION` o `EN_APROBACION`.
- **Información Visual:** Indicador de semáforo de tiempo restante de SLA (Verde: a tiempo; Amarillo: próximo a vencer; Rojo: vencido).
- **Acciones Directas:** Enlace a la mesa de revisión técnica con un solo clic.

---

## ⚖️ 7. Módulo 4: Mesa de Revisión Jurídica y Asistente IA

**Ruta:** `/api/v1/app/solicitud/{id}/revision`  
**Roles:** `REVISOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.

Esta es la pantalla central de trabajo para el abogado:
- **Visor Documental Integrado:** Permite leer el contrato en línea sin necesidad de descargarlo a su equipo local.
- **Panel Asistente de IA (Azure OpenAI):**
  - **Botón "Evaluar Riesgos Jurídicos":** La IA analiza el contrato completo y emite una lista de cláusulas de alto riesgo (penas convencionales desproporcionadas, jurisdicciones ambiguas, cesión de propiedad intelectual no deseada).
  - **Botón "Resumir Puntos Clave":** Genera un extracto ejecutivo de contraprestaciones, vigencia y causales de rescisión.
  - **Chat Jurídico Asistido:** Permite escribir preguntas libres sobre el contrato (ej. *"¿Cuál es el plazo de aviso previo para terminación anticipada según la cláusula décima?"*). La IA responde citando directamente el texto del documento.
- **Emisión de Dictamen:** El abogado selecciona si el documento es **Aceptable** (pasa a aprobación) o si cuenta con **Observaciones** (regresa al solicitante para corrección).

---

## 💬 8. Módulo 5: Hilos de Comentarios y Observaciones

**Ruta:** `/api/v1/app/solicitud/{id}/comentarios`  
**Roles:** `REVISOR_JURIDICO`, `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.

Permite mantener una conversación colaborativa estructurada directamente vinculada al expediente:
- Los comentarios soportan **respuestas anidadas (hilos jerárquicos)** para discutir cláusulas puntuales.
- Cada comentario registra el autor, su rol y la fecha/hora exacta.
- Los comentarios no pueden ser borrados ni alterados una vez enviados para garantizar la integridad del proceso.

---

## 🔄 9. Módulo 6: Control de Versiones e Inmutabilidad

**Ruta:** `/api/v1/app/solicitud/{id}/versiones`  
**Roles:** Todos los usuarios autorizados.

Cuando un contrato es observado, el usuario solicitante puede cargar una versión corregida:
- El sistema asigna automáticamente la versión consecutiva (`v1`, `v2`, `v3`...).
- Se calcula y exhibe el **hash SHA-256** del nuevo archivo.
- Permite descargar y comparar cualquier versión histórica para verificar exactamente qué cambios fueron introducidos entre una versión y otra.

---

## ✍️ 10. Módulo 7: Dictamen y Aprobación Formal

**Ruta:** `/api/v1/app/solicitud/{id}/aprobacion`  
**Roles:** `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.

El Aprobador Jurídico recibe las solicitudes que superaron la fase de revisión:
- Revisa el resumen del dictamen emitido por el revisor y el historial de observaciones resueltas.
- Opciones de resolución:
  - **Aprobar Documento:** Habilita el expediente para el proceso de firma electrónica.
  - **Rechazar Documento:** Da por concluido el trámite con estatus definitivo de rechazo legal.
  - **Regresar con Observaciones Adicionales:** Devuelve el expediente a la etapa de revisión.

---

## 🔏 11. Módulo 8: Registro de Firma Electrónica Criptográfica

**Ruta:** `/api/v1/app/solicitud/{id}/firma`  
**Roles:** `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`.

Formalización criptográfica del documento:
1. El aprobador visualiza el contrato final inmutable.
2. Ingresa su declaración formal de consentimiento y confirma su identidad.
3. El sistema genera un **sello de firma electrónica**:
   - Algoritmo: SHA-256 sobre el contenido del documento + ID del usuario firmante + Timestamp ISO 8601.
   - El estado de la solicitud transiciona permanentemente a `FIRMADO`.
   - Se genera una constancia de evidencia descargable con validez jurídica corporativa.

---

## 🕵️‍♂️ 12. Módulo 9: Bitácora de Auditoría y Trazabilidad Forense

**Ruta:** `/api/v1/app/trazabilidad`  
**Roles:** `AUDITOR`, `ADMINISTRADOR_PLATAFORMA`.

Pista de auditoría centralizada a prueba de manipulaciones:
- Registro de cada acción relevante: `CREACION_SOLICITUD`, `CAMBIO_ESTADO`, `ANALISIS_IA`, `DESCARGA_DOCUMENTO`, `EMISION_FIRMA`, `INICIO_SESION`.
- Campos registrados: Usuario, Correo, Rol, Acción, Entidad intervenida, Dirección IP cliente y Marca de tiempo exacta (UTC).
- Opciones de filtrado por rango de fechas, usuario o folio de solicitud.
- Exportación directa a formato CSV para auditorías externas o peritajes informáticos.

---

## 🛠️ 13. Módulo 10: Panel de Administración y Gestión de Usuarios

### A. Gestión de Usuarios y Roles
**Ruta:** `/api/v1/app/usuarios`  
**Roles:** `ADMINISTRADOR_PLATAFORMA`.
- Visualizar todos los usuarios registrados a través de Entra ID.
- Modificar el rol asignado a cada colaborador (`REVISOR_JURIDICO`, `APROBADOR_JURIDICO`, `AUDITOR`, `ADMINISTRADOR_PLATAFORMA`).
- Activar o suspender cuentas de colaboradores.

### B. Panel ORM Directo (SQLAdmin)
**Ruta:** `/admin`  
**Roles:** `ADMINISTRADOR_PLATAFORMA`.
- Gestión y consulta directa de modelos de base de datos relacional (`SolicitudRevision`, `Documento`, `VersionDocumento`, `Comentario`, `Firma`, `Auditoria`, `Workflow`).
- Protegido estrictamente con verificación de rol administrativo en sesión.

---

## 📈 14. Módulo 11: Tableros Analíticos en Power BI

**Ruta:** `/api/v1/analytics/powerbi-report` y `/powerbi/README_POWERBI.md`  
**Roles:** `ADMINISTRADOR_PLATAFORMA`, `AUDITOR`.

Monitoreo del desempeño operativo del departamento jurídico:
- **Tiempo de Ciclo Promedio (Turnaround Time - TAT):** Horas promedio desde el registro de una solicitud hasta su firma final.
- **Tasa de Cumplimiento de SLA:** Porcentaje de expedientes resueltos dentro del plazo comprometido.
- **Detección de Cuellos de Botella:** Identificación gráfica de revisores con acumulación de trabajo o expedientes detenidos en una misma etapa.
- **Volumen por Tipo de Contrato:** Distribución de carga por categorías documentales.
