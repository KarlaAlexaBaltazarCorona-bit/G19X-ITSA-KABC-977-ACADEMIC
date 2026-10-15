# LegalprojectIA ⚖️🤖

### Plataforma Integral de Workflow para Revisión Jurídica y Análisis Documental con Inteligencia Artificial (SaaS)

[![Despliegue en Azure](https://img.shields.io/badge/Azure-App%20Service-0078D4?logo=microsoftazure&logoColor=white)](https://legaltech-api-LegalprojectIA-1134.azurewebsites.net)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/Tests-58%20Passed%20(100%25)-success?logo=pytest&logoColor=white)](#-pruebas-unitarias-y-certificación-de-calidad)
[![DevSecOps](https://img.shields.io/badge/DevSecOps-Ruff%20%7C%20Bandit%20%7C%20Semgrep-purple?logo=githubactions&logoColor=white)](#-devsecops-y-seguridad-corporativa)
[![Licencia](https://img.shields.io/badge/Licencia-Privada%20%2F%20PluriOne-informational)](#)

---

**Entorno en Producción:** [https://legaltech-api-LegalprojectIA-1134.azurewebsites.net](https://legaltech-api-LegalprojectIA-1134.azurewebsites.net)  
**Organización Patrocinadora:** PluriOne S.A. de C.V. (Develop Talent & Technology)  
**Institución Académica:** Instituto Tecnológico Superior de Atlixco (ITSA) — Residencia Profesional  
**Estado:** 🏁 **Etapa Terminal / Listo para Entrega (100% de Historias de Usuario Completadas)**  

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fisc221977-cpu%2FNos-vamos-a-graduar%2Fmain%2Finfra%2Fazuredeploy.json)

> 📦 **Despliegue Llave en Mano "Click-to-Go":** Aprovisione toda la infraestructura corporativa de Microsoft Azure (PostgreSQL Flexible Server, App Service Linux, Azure OpenAI, Document Intelligence OCR, Blob Storage y AI Search) en 4 minutos con un solo clic. Consulte la [Guía de Entrega y Despliegue en Azure](docs/GUIA_ENTREGA_CLIENTE_AZURE.md).

---

## 📑 Tabla de Contenidos
1. [Visión General del Producto](#-visión-general-del-producto)
2. [Características Principales](#-características-principales)
3. [Matriz de Roles y Control de Acceso (RBAC)](#-matriz-de-roles-y-control-de-acceso-rbac)
4. [Centro de Documentación Oficial](#-centro-de-documentación-oficial)
5. [Inicio Rápido (Desarrollo Local)](#-inicio-rápido-desarrollo-local)
6. [Despliegue con Contenedores Docker](#-despliegue-con-contenedores-docker)
7. [Configuración de Microsoft Entra ID (SSO)](#-configuración-de-microsoft-entra-id-sso)
8. [Integración con Microsoft Power BI](#-integración-con-microsoft-power-bi)
9. [DevSecOps y Seguridad Corporativa](#-devsecops-y-seguridad-corporativa)
10. [Pruebas Unitarias y Certificación de Calidad](#-pruebas-unitarias-y-certificación-de-calidad)
11. [Stack Tecnológico Oficial](#-stack-tecnológico-oficial)

---

## 🌐 Visión General del Producto

**LegalprojectIA** es una solución de software como servicio (SaaS) concebida para modernizar la gestión contractual en áreas jurídicas corporativas y despachos legales. 

La plataforma articula el ciclo documental integral: desde la recepción de expedientes, asignación automática por balanceo de carga activa, análisis asistido por modelos avanzados de lenguaje (Azure OpenAI), hilos de discusión para observaciones, control de versiones inmutables y aprobaciones formales, hasta el estampado de firmas electrónicas con sellado criptográfico y trazabilidad forense.

```
Solicitud Creada ──► Asignación Balanceada ──► Revisión Jurídica + IA ──► Dictamen & Aprobación ──► Firma Electrónica
       │                                              │                                                    │
       ▼                                              ▼                                                    ▼
Folio Único & SLA                          Hilos de Comentarios & Versiones                       Hash SHA-256 Inmutable
```

---

## ✨ Características Principales

- 🔄 **Motor BPM y Balanceo de Carga (HU-01, HU-02, HU-03):** Asignación automática equitativa de contratos entrantes hacia el abogado revisor con menor carga activa de trabajo.
- 🧠 **Asistente Legal con Azure OpenAI (HU-14):** Integración con `gpt-5-mini` optimizado para análisis de riesgos contractuales, resumen ejecutivo de cláusulas y consultas jurídicas interactivas con contexto denso.
- 📄 **Extracción Híbrida Digital + OCR:** Pipeline de procesamiento ultrarrápido con PyMuPDF y contingencia automática (*fallback*) mediante **Azure AI Document Intelligence** para contratos escaneados o imágenes.
- 🔒 **Inmutabilidad y Control de Versiones (HU-08, HU-09):** Cada ajuste genera una versión incremental con su resumen criptográfico SHA-256 (64 caracteres) garantizando la autenticidad e imposibilidad de alteración retroactiva.
- ✍️ **Dictamen y Firma Electrónica (HU-10, HU-11):** Resolución formal por parte de directores o aprobadores con sellado de tiempo y certificado de evidencia digital para no repudio.
- 🕵️‍♂️ **Pista de Auditoría Forense (HU-12):** Bitácora inalterable que documenta usuario, rol, IP de origen, entidad intervenida y timestamp UTC de cada evento en la plataforma.
- 📊 **Inteligencia de Negocio y Power BI:** Vistas SQL nativas y endpoints REST para dashboards ejecutivos con cálculo de Turnaround Time (TAT), cumplimiento de SLAs y detección de cuellos de botella.
- 🛡️ **Seguridad Grado Corporativo:** Autenticación institucional Microsoft Entra ID (SSO), cifrado en reposo AES-256-GCM, Rate Limiting y blindaje contra el OWASP Top 10.
- 🛠️ **Panel Administrativo (HU-15):** Interfaz ORM embebida (SQLAdmin) y catálogo de gestión de colaboradores para administradores de plataforma.

---

## 👥 Matriz de Roles y Control de Acceso (RBAC)

La plataforma aplica segregación estricta de responsabilidades a nivel de endpoint:

| Rol Oficial | Icono | Descripción y Alcance Operativo |
| :--- | :---: | :--- |
| **`REVISOR_JURIDICO`** | ⚖️ | Abogados dictaminadores. Reciben solicitudes por balanceo, interactúan con la IA, comentan y emiten dictámenes preliminares. |
| **`APROBADOR_JURIDICO`** | ✒️ | Directores y apoderados legales. Evalúan dictámenes, resuelven aprobaciones o rechazos definitivos y ejecutan la firma electrónica. |
| **`AUDITOR`** | 🔍 | Oficiales de cumplimiento y contraloría interna. Acceso de solo lectura a la bitácora de auditoría forense, métricas y reportes Power BI. |
| **`ADMINISTRADOR_PLATAFORMA`** | ⚙️ | TI y operaciones. Supervisión global, alta de usuarios, asignación de roles, panel SQLAdmin y saneamiento de registros. |

---

## 📚 Centro de Documentación Oficial

El repositorio incluye una exhaustiva suite de documentación técnica y operativa en el directorio [`docs/`](docs/):

- [📘 **Manual de Usuario y Roles**](docs/MANUAL_USUARIO_Y_ROLES.md) — Guía interactiva paso a paso de los 11 módulos del portal y perfiles de acceso.
- [🏛️ **Arquitectura del Sistema**](docs/ARQUITECTURA_SISTEMA.md) — Diagramas de nube en Azure, modelo C4 de contenedores, máquina de estados BPM y ERD de base de datos.
- [📋 **Matriz de Historias de Usuario (HU-01 a HU-17)**](docs/MATRIZ_HISTORIAS_USUARIO.md) — Trazabilidad formal de requerimientos, criterios de aceptación y pruebas de verificación al 100%.
- [📡 **Referencia de la API RESTful (v1)**](docs/API_REFERENCE.md) — Especificación técnica de endpoints, cabeceras, parámetros, payloads y códigos de respuesta.
- [🛡️ **Seguridad Corporativa y DevSecOps**](docs/SEGURIDAD_Y_DEVSECOPS.md) — Mitigación OWASP Top 10, criptografía AES-256-GCM, pipeline CI/CD y políticas de auditoría.
- [📦 **Guía de Entrega y Despliegue en Azure**](docs/GUIA_ENTREGA_CLIENTE_AZURE.md) — Procedimiento de aprovisionamiento llave en mano mediante plantillas ARM y Bicep.
- [📊 **Guía de Integración con Power BI**](powerbi/README_POWERBI.md) — Conexión nativa a Azure PostgreSQL, feeds REST y medidas DAX preconstruidas.
- [🧭 **Índice Maestro de Documentación**](docs/INDEX.md) — Directorio completo de navegación documental.

---

## 🚀 Inicio Rápido (Desarrollo Local)

### 1. Prerrequisitos
- Python 3.11 o superior
- PostgreSQL 16 (local o contenedor Docker)
- Git

### 2. Clonación y Entorno Virtual
```bash
# Clonar el repositorio
git clone https://github.com/isc221977-cpu/Nos-vamos-a-graduar.git LegalprojectIA
cd LegalprojectIA

# Crear y activar entorno virtual
python -m venv .venv
# En Windows (PowerShell):
.venv\Scripts\activate
# En Linux/macOS:
# source .venv/bin/activate

# Instalar dependencias congeladas
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno
```bash
cp .env.example .env
# Edita el archivo .env con tus credenciales de base de datos y servicios Azure
```

### 4. Base de Datos y Migraciones
```bash
# (Opcional) Levantar PostgreSQL localmente con Docker Compose
docker compose -f docker-compose.dev.yml up -d

# Ejecutar las migraciones de esquema con Alembic
alembic upgrade head
```

### 5. Iniciar la Aplicación
```bash
python main.py
```

Puntos de acceso en el explorador:
- **Portal de Acceso (Login):** [http://localhost:8000/login](http://localhost:8000/login)
- **Dashboard Principal:** [http://localhost:8000/api/v1/app/dashboard](http://localhost:8000/api/v1/app/dashboard)
- **Documentación Interactiva Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Panel Administrativo ORM:** [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 🐳 Despliegue con Contenedores Docker

Para ejecutar la solución completa (backend FastAPI y base de datos PostgreSQL) en contenedores:

```bash
# Construir e iniciar contenedores en segundo plano
docker compose up -d --build

# Comprobar el estado operativo
docker compose ps

# Ver registros de la aplicación
docker compose logs -f app
```

---

## 🔐 Configuración de Microsoft Entra ID (SSO)

Para habilitar la autenticación corporativa vía Microsoft 365:

```env
ENTRA_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # Application (client) ID
ENTRA_TENANT_ID=common                                 # Multi-tenant o Tenant ID específico
```

**Configuración en Azure Portal:**
1. Navegue a **Microsoft Entra ID** → **App registrations** → Registre su aplicación (`LegalprojectIA`).
2. En **Authentication** → **Redirect URIs**, configure:
   - `http://localhost:8000/login` (desarrollo local)
   - `https://legaltech-api-LegalprojectIA-1134.azurewebsites.net/login` (producción)
3. En **App roles**, configure los 4 roles del sistema: `REVISOR_JURIDICO`, `APROBADOR_JURIDICO`, `ADMINISTRADOR_PLATAFORMA`, `AUDITOR`.

---

## 📊 Integración con Microsoft Power BI

La plataforma ofrece conexión directa para tableros ejecutivos:
1. **Método A (SQL Directo):** Conectar Power BI a Azure PostgreSQL utilizando las vistas optimizadas de `powerbi/vistas_powerbi.sql` (`vw_powerbi_solicitudes_kpi`, `vw_powerbi_cuellos_botella`, `vw_powerbi_trazabilidad`).
2. **Método B (REST Feed):** Consumir el endpoint web `/api/v1/analytics/powerbi-feed` con la cabecera `X-API-KEY`.

Consulte la [Guía Completa de Power BI](powerbi/README_POWERBI.md) para fórmulas DAX preconstruidas de SLA, TAT y cuellos de botella.

---

## 🛡️ DevSecOps y Seguridad Corporativa

El repositorio incorpora controles de seguridad continuos antes de cada entrega:
- **Cifrado en Reposo:** Campos clasificados asegurados con **AES-256-GCM** y nonces únicos por registro.
- **Integridad de Archivos:** Resumen criptográfico **SHA-256** para cada versión de documento.
- **Protección contra Fuzzing y DoS:** Limitador de tasa (*Rate Limiter*) y límite estricto de cuerpo de petición (20 MB).
- **Anti-Fingerprinting:** Supresión de huellas de servidor (`Server: uvicorn`) y cabeceras OWASP (CSP, HSTS, X-Frame-Options: DENY).
- **Escaneo Continuo:** Pipeline en GitHub Actions que ejecuta `ruff`, `semgrep`, `bandit`, `pip-audit` y `pytest`.

---

## 🧪 Pruebas Unitarias y Certificación de Calidad

La solución cuenta con una suite automatizada de **58 pruebas unitarias y de integración** que abarcan control de acceso, IA, analítica, auditoría, criptografía y ciclo de vida de expedientes:

```bash
# Ejecutar todas las pruebas con pytest
pytest -v
```

**Resultado:**
```text
======================= 58 passed in 26.45s =======================
```

---

## 🛠️ Stack Tecnológico Oficial

| Componente | Tecnología |
| :--- | :--- |
| **Lenguaje y Framework Backend** | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| **Persistencia y ORM** | PostgreSQL 16, SQLAlchemy 2.0, Alembic |
| **Frontend Ligero** | Jinja2 Templates, HTML5, CSS3, TailwindCSS, MSAL.js local |
| **Servicios Cloud Cognitivos** | Azure OpenAI (`gpt-5-mini`), Azure AI Document Intelligence |
| **Procesamiento de Archivos** | PyMuPDF, DefusedXML, Python-Docx |
| **Almacenamiento de Archivos** | Azure Blob Storage (StorageV2) |
| **Búsqueda Vectorial** | Azure AI Search |
| **Seguridad e Identidad** | Microsoft Entra ID (OAuth2 / OIDC), Cryptography (AES-256-GCM) |
| **Panel Administrativo** | SQLAdmin |
| **Inteligencia de Negocio** | Microsoft Power BI Desktop & Service |
| **Infraestructura como Código (IaC)** | Azure Resource Manager (ARM), Bicep, PowerShell, Bash |
| **DevSecOps & CI/CD** | GitHub Actions, Ruff, Bandit, Semgrep, pip-audit, Pytest |

---

## 🤝 Contribución y Buenas Prácticas

Consulte nuestro documento [CONTRIBUTING.md](CONTRIBUTING.md) para conocer las directrices de contribución, convención de ramas y commits por Historias de Usuario, y los 5 filtros de validación obligatoria pre-push.

---

## ⚖️ Licencia y Créditos

Desarrollado como proyecto de titulación por Residencia Profesional para **PluriOne S.A. de C.V.** en vinculación con el **Instituto Tecnológico Superior de Atlixco (ITSA)**.  
*Todos los derechos reservados © 2026 PluriOne S.A. de C.V.*
