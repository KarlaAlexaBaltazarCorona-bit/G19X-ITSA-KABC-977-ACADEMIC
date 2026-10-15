# 📚 Centro de Documentación Oficial — LegalprojectIA
## Plataforma de Workflow para Revisión Jurídica con Inteligencia Artificial (SaaS)

Bienvenido al centro neurálgico de documentación técnica, funcional y de operaciones de **LegalprojectIA**, desarrollada en colaboración entre **PluriOne S.A. de C.V.** y el **Instituto Tecnológico Superior de Atlixco (ITSA)**.

---

## 🧭 Mapa de Navegación Documental

| Documento | Audiencia Principal | Descripción |
| :--- | :--- | :--- |
| [📘 **Manual de Usuario y Roles**](MANUAL_USUARIO_Y_ROLES.md) | Abogados, Aprobadores, Auditores, Administradores | Guía operativa paso a paso de los 11 módulos de la plataforma, roles RBAC y flujos de trabajo. |
| [🏛️ **Arquitectura del Sistema**](ARQUITECTURA_SISTEMA.md) | Arquitectos de Software, Líderes Técnicos | Especificación de arquitectura Cloud en Azure, Modelo C4, motor BPM, orquestación de IA y ERD relacional. |
| [📋 **Matriz de Historias de Usuario**](MATRIZ_HISTORIAS_USUARIO.md) | Comités Evaluadores, Product Owners, Scrum Masters | Trazabilidad integral de las 17 Historias de Usuario (HU-01 a HU-17) con criterios de aceptación y pruebas. |
| [📡 **Referencia de la API RESTful**](API_REFERENCE.md) | Desarrolladores, Integradores de Sistemas | Catálogo exhaustivo de endpoints `/api/v1/`, parámetros, modelos de datos, autenticación y códigos de error. |
| [🛡️ **Seguridad y DevSecOps**](SEGURIDAD_Y_DEVSECOPS.md) | Oficiales de Seguridad (CISO), Equipos DevOps | Mitigación OWASP Top 10, criptografía AES-256-GCM, pipeline CI/CD, auditoría forense y RBAC. |
| [📦 **Guía de Entrega y Despliegue en Azure**](GUIA_ENTREGA_CLIENTE_AZURE.md) | Equipos de Cloud Operations, TI de Clientes | Despliegue "Click-to-Go" automatizado en Azure con ARM, Bicep y aprovisionamiento *zero-touch*. |
| [📊 **Guía de Integración con Power BI**](../powerbi/README_POWERBI.md) | Analistas de Datos, Directores Jurídicos | Conexión de Power BI Desktop/Service a vistas SQL de PostgreSQL y feeds REST, con fórmulas DAX listas para usar. |

---

## 🚀 Resumen del Ecosistema de la Plataforma

```
                                  ┌───────────────────────────┐
                                  │      LegalprojectIA       │
                                  │  (Plataforma SaaS Legal)  │
                                  └─────────────┬─────────────┘
                                                │
         ┌────────────────────────┬─────────────┴─────────────┬────────────────────────┐
         ▼                        ▼                           ▼                        ▼
 ┌───────────────┐        ┌───────────────┐           ┌───────────────┐        ┌───────────────┐
 │   Frontend    │        │  Backend API  │           │ Servicios IA  │        │   Analítica   │
 │   Modular     │        │    FastAPI    │           │ Azure OpenAI  │        │   Power BI    │
 │ (Jinja2 + JS) │        │ (Python 3.11) │           │ + Doc Intel   │        │ (Vistas SQL)  │
 └───────────────┘        └───────────────┘           └───────────────┘        └───────────────┘
```

---

## 🎯 Puntos de Acceso en Producción y Desarrollo

- **URL de Producción:** https://legaltech-api-LegalprojectIA-1134.azurewebsites.net
- **Portal de Acceso (Login):** `/login`
- **Dashboard Principal:** `/api/v1/app/dashboard`
- **Documentación Interactiva Swagger:** `/docs` (disponible en entorno local o con `ENABLE_DOCS=true`)
- **Panel Administrativo ORM:** `/admin` (requiere credenciales con rol `ADMINISTRADOR_PLATAFORMA`)
- **Reportes Analíticos:** `/api/v1/analytics/powerbi-report`

---

## 🧪 Estado de Pruebas y Certificación de Calidad

- **Pruebas Automatizadas:** 58/58 pruebas superadas (100% éxito en `pytest`).
- **Análisis de Código Estático (Linter):** 0 advertencias / 0 errores en `ruff check .`.
- **Análisis de Vulnerabilidades (SAST):** Aprobado con `bandit` y `semgrep`.
- **Auditoría de Dependencias (CVEs):** Sin vulnerabilidades reportadas en `pip-audit`.
