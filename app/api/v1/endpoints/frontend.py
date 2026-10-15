"""
frontend.py — Endpoints que sirven las páginas HTML del portal interno de PluriOne.
══════════════════════════════════════════════════════════════════════════════════════════════

ARQUITECTURA:
  Este archivo es la "Capa de Interfaz" del frontend.
  Cada función recibe el token de Entra ID (del sessionStorage del navegador),
  verifica el rol del usuario, y devuelve la página HTML correspondiente.

CÓMO FUNCIONA EL FLUJO:
  1. El navegador hace GET /app/<pantalla> con header Authorization: Bearer <token>
  2. get_current_user() verifica el token y extrae el rol
  3. requiere_roles() verifica que ese rol tiene acceso a esa pantalla
  4. Se renderiza el HTML con Jinja2 (templates en app/templates/)
  5. El HTML se devuelve al navegador

  MATRIZ DE ROLES × PANTALLAS:
  - Dashboard:           TODOS los roles
  - Bandeja de trabajo:  REVISOR_JURIDICO, APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
  - Documentos:          TODOS los roles
  - Nueva solicitud:     REVISOR_JURIDICO, APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
  - Revisión jurídica:   REVISOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
  - Comentarios:         REVISOR_JURIDICO, APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
  - Historial versiones: APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
  - Aprobación:          APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
  - Firma electrónica:   APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
  - Trazabilidad:        AUDITOR, ADMINISTRADOR_PLATAFORMA
  - Panel admin:         ADMINISTRADOR_PLATAFORMA
  - Registro usuarios:   ADMINISTRADOR_PLATAFORMA
"""

from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.roles_guard import requiere_roles
from app.models.user import RolUsuario

router = APIRouter()

# Carpeta de plantillas Jinja2 (relativa a este archivo)
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.globals["get_flashed_messages"] = lambda *args, **kwargs: []


def render_page(request: Request, template_name: str, context: dict) -> HTMLResponse:
    """Renderiza una plantilla Jinja2 con la firma estandar y moderna de Starlette."""
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context,
    )

# ── Todos los roles ─────────────────────────────────────────────────────────
ROLES_TODOS = (
    RolUsuario.REVISOR_JURIDICO.value,
    RolUsuario.APROBADOR_JURIDICO.value,
    RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    RolUsuario.AUDITOR.value,
)

# ── Menú lateral filtrado por rol ───────────────────────────────────────────
# Cada ítem tiene: id (de la pantalla en el diseño), label, url, icon (Lucide),
# y la lista de roles que pueden verlo.
MENU_ITEMS = [
    {"id": 2,  "label": "Dashboard",         "url": "/api/v1/app/dashboard",   "icon": "layout-dashboard",
     "roles": list(ROLES_TODOS)},
    {"id": 3,  "label": "Mis tareas",         "url": "/api/v1/app/tareas",      "icon": "list-checks",
     "roles": [RolUsuario.REVISOR_JURIDICO.value, RolUsuario.APROBADOR_JURIDICO.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value]},
    {"id": 4,  "label": "Solicitudes",        "url": "/api/v1/app/solicitudes", "icon": "folder-open",
     "roles": list(ROLES_TODOS)},
    {"id": 5,  "label": "Nueva solicitud",    "url": "/api/v1/app/nueva",       "icon": "file-plus-2",
     "roles": [RolUsuario.REVISOR_JURIDICO.value, RolUsuario.APROBADOR_JURIDICO.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value]},
    {"id": 11, "label": "Trazabilidad",       "url": "/api/v1/app/trazabilidad","icon": "history",
     "roles": [RolUsuario.AUDITOR.value, RolUsuario.ADMINISTRADOR_PLATAFORMA.value]},
    {"id": 12, "label": "Panel admin",        "url": "/api/v1/app/admin",       "icon": "settings",
     "roles": [RolUsuario.ADMINISTRADOR_PLATAFORMA.value]},
    {"id": 13, "label": "Usuarios",           "url": "/api/v1/app/usuarios",    "icon": "users",
     "roles": [RolUsuario.ADMINISTRADOR_PLATAFORMA.value]},
]

def _ctx(request: Request, usuario: dict, page_title: str, **extra):
    """
    Construye el contexto base que toda plantilla necesita.
    Incluye: request, usuario actual, rol, menú filtrado por rol y
    cualquier dato extra específico de la página.
    """
    rol = usuario["rol"]
    menu = [item for item in MENU_ITEMS if rol in item["roles"]]
    return {
        "request":       request,
        "current_user":  usuario,
        "current_role":  rol,
        "page_title":    page_title,
        "menu_items":    menu,
        **extra,
    }

# ════════════════════════════════════════════════════════════════
# PANTALLA 2: Dashboard / Inicio
# Acceso: TODOS los roles
# ════════════════════════════════════════════════════════════════
@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def page_dashboard(
    request: Request,
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """
    Página de inicio personalizada por rol.
    Muestra KPIs y accesos rápidos según si el usuario es
    Revisor Jurídico, Aprobador Jurídico, Admin o Auditor.
    """
    return render_page(request,
        "dashboard.html",
        _ctx(request, usuario, "Dashboard"),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 3: Bandeja de trabajo (Mis tareas)
# Acceso: REVISOR_JURIDICO, APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/tareas", response_class=HTMLResponse, include_in_schema=False)
def page_tareas(
    request: Request,
    usuario: dict = Depends(requiere_roles(
        RolUsuario.REVISOR_JURIDICO.value,
        RolUsuario.APROBADOR_JURIDICO.value,
        RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    )),
):
    """
    Listado de solicitudes asignadas al usuario autenticado.
    Los datos reales vienen de /api/v1/workflows/inbox (llamada AJAX desde el frontend).
    """
    return render_page(request,
        "tasks.html",
        _ctx(request, usuario, "Mis tareas"),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 4: Solicitudes (antes "Documentos")
# Acceso: TODOS los roles
# ════════════════════════════════════════════════════════════════
@router.get("/solicitudes", response_class=HTMLResponse, include_in_schema=False)
def page_solicitudes(
    request: Request,
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """
    Listado general de solicitudes de revisión jurídica.
    """
    return render_page(request,
        "documents.html",
        _ctx(request, usuario, "Solicitudes"),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 4b: Detalle de solicitud
# Acceso: TODOS los roles
# ════════════════════════════════════════════════════════════════
@router.get("/solicitudes/{solicitud_id}", response_class=HTMLResponse, include_in_schema=False)
def page_solicitud_detalle(
    solicitud_id: str,
    request: Request,
    usuario: dict = Depends(requiere_roles(*ROLES_TODOS)),
):
    """
    Información general de una solicitud: responsable, estado, fechas, participantes.
    Ventana de contexto dentro de la lista de solicitudes.
    """
    return render_page(request,
        "document_detail.html",
        _ctx(request, usuario, "Detalle de solicitud", solicitud_id=solicitud_id),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 5: Nueva solicitud
# Acceso: REVISOR_JURIDICO, APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/nueva", response_class=HTMLResponse, include_in_schema=False)
def page_nueva_solicitud(
    request: Request,
    usuario: dict = Depends(requiere_roles(
        RolUsuario.REVISOR_JURIDICO.value,
        RolUsuario.APROBADOR_JURIDICO.value,
        RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    )),
):
    """
    Formulario para subir un documento e iniciar un proceso de revisión.
    El POST va a /api/v1/solicitudes/ (endpoint en solicitudes.py).
    """
    return render_page(request,
        "new_document.html",
        _ctx(request, usuario, "Nueva solicitud"),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 6: Revisión jurídica + Análisis con IA
# Acceso: REVISOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/revision/{solicitud_id}", response_class=HTMLResponse, include_in_schema=False)
def page_revision(
    solicitud_id: str,
    request: Request,
    usuario: dict = Depends(requiere_roles(
        RolUsuario.REVISOR_JURIDICO.value,
        RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    )),
):
    """
    Pantalla principal de revisión jurídica.
    Incluye: vista del documento, formulario de observaciones/correcciones
    y el panel de Análisis con IA (chat de IA a la derecha).
    """
    return render_page(request,
        "legal_review.html",
        _ctx(request, usuario, "Revisión jurídica", solicitud_id=solicitud_id),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 7: Comentarios colaborativos
# Acceso: REVISOR_JURIDICO, APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/comentarios/{solicitud_id}", response_class=HTMLResponse, include_in_schema=False)
def page_comentarios(
    solicitud_id: str,
    request: Request,
    usuario: dict = Depends(requiere_roles(
        RolUsuario.REVISOR_JURIDICO.value,
        RolUsuario.APROBADOR_JURIDICO.value,
        RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    )),
):
    """
    Hilo de comentarios y respuestas sobre una solicitud.
    Permite a revisores y aprobadores comunicarse sin salir de la plataforma.
    """
    return render_page(request,
        "comments.html",
        _ctx(request, usuario, "Comentarios colaborativos", solicitud_id=solicitud_id),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 8: Historial de versiones
# Acceso: APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/versiones/{solicitud_id}", response_class=HTMLResponse, include_in_schema=False)
def page_versiones(
    solicitud_id: str,
    request: Request,
    usuario: dict = Depends(requiere_roles(
        RolUsuario.APROBADOR_JURIDICO.value,
        RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    )),
):
    """
    Historial de versiones del documento adjunto a una solicitud.
    Permite comparar cambios entre versiones (HU-08, HU-09).
    """
    return render_page(request,
        "version_history.html",
        _ctx(request, usuario, "Historial de versiones", solicitud_id=solicitud_id),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 9: Aprobación / Rechazo
# Acceso: APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/aprobacion/{solicitud_id}", response_class=HTMLResponse, include_in_schema=False)
def page_aprobacion(
    solicitud_id: str,
    request: Request,
    usuario: dict = Depends(requiere_roles(
        RolUsuario.APROBADOR_JURIDICO.value,
        RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    )),
):
    """
    Pantalla de decisión final: aprobar, rechazar o solicitar cambios.
    El POST va a /api/v1/solicitudes/{id}/decision.
    """
    return render_page(request,
        "approval.html",
        _ctx(request, usuario, "Aprobación / Rechazo", solicitud_id=solicitud_id),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 10: Firma electrónica
# Acceso: APROBADOR_JURIDICO, ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/firma/{solicitud_id}", response_class=HTMLResponse, include_in_schema=False)
def page_firma(
    solicitud_id: str,
    request: Request,
    usuario: dict = Depends(requiere_roles(
        RolUsuario.APROBADOR_JURIDICO.value,
        RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    )),
):
    """
    Pantalla de firma electrónica de solicitudes aprobadas.
    Incluye validación opcional con Azure Document Intelligence.
    """
    return render_page(request,
        "signature.html",
        _ctx(request, usuario, "Firma electrónica", solicitud_id=solicitud_id),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 11: Trazabilidad / Historial
# Acceso: AUDITOR, ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/trazabilidad", response_class=HTMLResponse, include_in_schema=False)
def page_trazabilidad(
    request: Request,
    usuario: dict = Depends(requiere_roles(
        RolUsuario.AUDITOR.value,
        RolUsuario.ADMINISTRADOR_PLATAFORMA.value,
    )),
):
    """
    Registro completo de auditoría: quién hizo qué, cuándo y desde dónde (HU-12).
    Vista de solo lectura para el Auditor.
    """
    return render_page(request,
        "traceability.html",
        _ctx(request, usuario, "Trazabilidad"),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 12: Panel administrativo
# Acceso: ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def page_admin(
    request: Request,
    usuario: dict = Depends(requiere_roles(RolUsuario.ADMINISTRADOR_PLATAFORMA.value)),
):
    """
    Panel de administración: KPIs globales, accesos rápidos y configuración.
    Para gestión completa de tablas ver también /admin (SQLAdmin).
    """
    return render_page(request,
        "admin_panel.html",
        _ctx(request, usuario, "Panel administrativo"),
    )

# ════════════════════════════════════════════════════════════════
# PANTALLA 13: Registro de usuarios y funcionarios
# Acceso: ADMINISTRADOR_PLATAFORMA
# ════════════════════════════════════════════════════════════════
@router.get("/usuarios", response_class=HTMLResponse, include_in_schema=False)
def page_usuarios(
    request: Request,
    usuario: dict = Depends(requiere_roles(RolUsuario.ADMINISTRADOR_PLATAFORMA.value)),
):
    """
    Gestión de usuarios internos: alta, baja, cambio de rol.
    Los 5 roles disponibles son los definidos en ROLES.txt del proyecto.
    """
    return render_page(request,
        "user_registration.html",
        _ctx(request, usuario, "Usuarios y funcionarios"),
    )
