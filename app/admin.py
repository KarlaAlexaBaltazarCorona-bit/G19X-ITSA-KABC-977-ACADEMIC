"""Panel administrativo automático ("Django" -> equivalente en FastAPI).

Django trae un admin panel automático que ahorra construir a mano las
Pantallas 12 (Panel administrativo) y 13 (Usuarios y funcionarios). Como el
backend está en FastAPI (no se migra a Django), el equivalente directo es
**SQLAdmin**: genera un panel CRUD a partir de los mismos modelos SQLAlchemy
que ya tenemos, sin cambiar de framework ni duplicar lógica.

Se monta en `/admin` desde app/main.py. En producción, protegerlo detrás de
autenticación es responsabilidad de quien lo despliegue (por ejemplo, solo
accesible dentro de la red interna o de una VPN) -- SQLAdmin no reutiliza
automáticamente `requiere_roles(...)` porque no es una ruta de FastAPI normal.
"""

import secrets

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.models.audit import Auditoria
from app.models.comment import Comentario
from app.models.document import Documento
from app.models.extras import ChatMensaje, Firma, Notificacion
from app.models.revision import Revision
from app.models.solicitud import SolicitudRevision
from app.models.tenant import TenantModel
from app.models.user import Usuario
from app.models.version import VersionDocumento
from app.models.workflow import WorkflowTaskModel


class AdminAuth(AuthenticationBackend):
    """Control de acceso estricto para el panel SQLAdmin.

    Exige que el usuario esté autenticado con Microsoft Entra ID con rol
    ADMINISTRADOR_PLATAFORMA, o posea las credenciales maestras del sistema.
    Cualquier intento no autorizado es bloqueado y redirigido a login.
    """

    async def login(self, request: Request) -> bool:
        form = await request.form()
        password = str(form.get("password") or "").strip()

        if password and settings.APP_API_KEY and secrets.compare_digest(password, settings.APP_API_KEY):
            request.session.update({"admin_auth": True, "admin_role": "ADMINISTRADOR_PLATAFORMA"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        # 1. Sesión activa de administrador en cookie de sesión
        if request.session.get("admin_auth") and request.session.get("admin_role") == "ADMINISTRADOR_PLATAFORMA":
            return True

        # 2. Token de Microsoft Entra ID en cookies del navegador o cabecera Bearer
        token = request.cookies.get("plurione_auth_token") or request.cookies.get("access_token")
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if token:
            try:
                from app.core.auth_guard import _decode_token_claims
                claims = _decode_token_claims(token)
                email = (claims.get("preferred_username") or claims.get("email") or claims.get("upn") or "").lower().strip()
                admin_config = (getattr(settings, "INITIAL_ADMIN_EMAIL", None) or "").lower().strip()

                from app.core.database import SessionLocal
                from app.models.user import RolUsuario, Usuario
                db = SessionLocal()
                try:
                    user = db.query(Usuario).filter(Usuario.correo == email).first()
                    if (user and user.activo and user.role == RolUsuario.ADMINISTRADOR_PLATAFORMA) or (admin_config and email == admin_config):
                        request.session.update({"admin_auth": True, "admin_role": "ADMINISTRADOR_PLATAFORMA", "email": email})
                        return True
                finally:
                    db.close()
            except Exception:
                pass

        # 3. Llave maestra X-API-KEY
        api_key = request.headers.get("x-api-key")
        if api_key and settings.APP_API_KEY and secrets.compare_digest(api_key, settings.APP_API_KEY):
            return True

        # No autorizado
        return False


class UsuarioAdmin(ModelView, model=Usuario):
    """Pantalla 13 (Usuarios y funcionarios) resuelta automáticamente por SQLAdmin."""

    name = "Usuario"
    name_plural = "Usuarios"
    column_list = [Usuario.id, Usuario.nombre, Usuario.apellido, Usuario.correo, Usuario.role, Usuario.activo]
    column_searchable_list = [Usuario.nombre, Usuario.correo]
    column_sortable_list = [Usuario.nombre, Usuario.role, Usuario.activo]

    async def on_model_delete(self, model: Usuario, request: Request) -> None:
        """Reasigna dependencias de claves foráneas antes de eliminar para prevenir IntegrityError."""
        from app.core.database import SessionLocal
        from app.models.audit import Auditoria
        from app.models.comment import Comentario
        from app.models.extras import ChatMensaje, Firma, Notificacion
        from app.models.revision import Revision
        from app.models.solicitud import SolicitudRevision
        from app.models.user import RolUsuario
        from app.models.workflow import WorkflowTaskModel

        with SessionLocal() as db:
            admin_user = (
                db.query(Usuario)
                .filter(Usuario.role == RolUsuario.ADMINISTRADOR_PLATAFORMA)
                .filter(Usuario.id != model.id)
                .first()
            )
            admin_id = admin_user.id if admin_user else None
            if admin_id:
                db.query(SolicitudRevision).filter(SolicitudRevision.requested_id == model.id).update({"requested_id": admin_id})
                db.query(SolicitudRevision).filter(SolicitudRevision.revicion_id == model.id).update({"revicion_id": None})
                db.query(Revision).filter(Revision.revizado_id == model.id).update({"revizado_id": admin_id})
                db.query(Comentario).filter(Comentario.user_id == model.id).update({"user_id": admin_id})
                db.query(Auditoria).filter(Auditoria.user_id == model.id).update({"user_id": admin_id})
                db.query(Firma).filter(Firma.firmante_id == model.id).update({"firmante_id": admin_id})
                db.query(WorkflowTaskModel).filter(WorkflowTaskModel.revisor_id == model.id).update({"revisor_id": admin_id})
                db.query(ChatMensaje).filter(ChatMensaje.autor_id == model.id).update({"autor_id": admin_id})
                db.query(Notificacion).filter(Notificacion.user_id == model.id).delete()
                db.commit()


class SolicitudAdmin(ModelView, model=SolicitudRevision):
    """Pantalla 12 (Panel administrativo): vista general de todas las solicitudes."""

    name = "Solicitud de Revisión"
    name_plural = "Solicitudes de Revisión"
    column_list = [
        SolicitudRevision.id,
        SolicitudRevision.titulo,
        SolicitudRevision.estado,
        SolicitudRevision.prioridad,
        SolicitudRevision.requested_id,
        SolicitudRevision.revicion_id,
    ]
    column_searchable_list = [SolicitudRevision.titulo, SolicitudRevision.numero_respuesta]
    column_sortable_list = [SolicitudRevision.estado, SolicitudRevision.creado_at]


class DocumentoAdmin(ModelView, model=Documento):
    column_list = [Documento.id, Documento.nombre, Documento.tipo_documento, Documento.solicitud_id]


class VersionDocumentoAdmin(ModelView, model=VersionDocumento):
    column_list = [VersionDocumento.id, VersionDocumento.documento_id, VersionDocumento.numero_version, VersionDocumento.nombre_archivo]


class RevisionAdmin(ModelView, model=Revision):
    column_list = [Revision.id, Revision.solicitud_id, Revision.revizado_id, Revision.decision, Revision.estado]


class ComentarioAdmin(ModelView, model=Comentario):
    column_list = [Comentario.id, Comentario.solicitud_id, Comentario.user_id, Comentario.resuelto]


class AuditoriaAdmin(ModelView, model=Auditoria):
    can_create = False  # la auditoría solo se crea desde el código, nunca a mano
    can_edit = False
    can_delete = False
    column_list = [Auditoria.id, Auditoria.solicitud_id, Auditoria.tipo_documento, Auditoria.accion, Auditoria.creada_at]


class FirmaAdmin(ModelView, model=Firma):
    column_list = [Firma.id, Firma.solicitud_id, Firma.firmante_id, Firma.estado]


class NotificacionAdmin(ModelView, model=Notificacion):
    column_list = [Notificacion.id, Notificacion.user_id, Notificacion.titulo, Notificacion.leida]


class TenantAdmin(ModelView, model=TenantModel):
    """Catálogo de organizaciones/empresas."""

    name = "Organización"
    name_plural = "Organizaciones"
    column_list = [TenantModel.id, TenantModel.nombre_comercial, TenantModel.rfc, TenantModel.activo]
    column_searchable_list = [TenantModel.nombre_comercial, TenantModel.rfc]


class WorkflowTaskAdmin(ModelView, model=WorkflowTaskModel):
    """Tareas de workflow (tabla `workflow_tasks` -- reservada para flujos futuros)."""

    name = "Tarea Workflow"
    name_plural = "Tareas Workflow"
    column_list = [WorkflowTaskModel.id, WorkflowTaskModel.document_id, WorkflowTaskModel.revisor_id, WorkflowTaskModel.etapa, WorkflowTaskModel.estado]


class ChatMensajeAdmin(ModelView, model=ChatMensaje):
    can_create = False
    can_edit = False
    column_list = [ChatMensaje.id, ChatMensaje.solicitud_id, ChatMensaje.rol_mensaje]


def registrar_admin(app, engine) -> Admin:
    """Crea y monta el panel SQLAdmin en `/admin` con autenticación obligatoria."""
    secret = settings.APP_ENCRYPTION_KEY or settings.APP_API_KEY or "sqladmin-session-secret-key-2026"
    admin_auth = AdminAuth(secret_key=secret)
    admin = Admin(
        app,
        engine,
        title="LegalTech - Panel Administrativo",
        authentication_backend=admin_auth,
    )
    for vista in (
        UsuarioAdmin,
        SolicitudAdmin,
        DocumentoAdmin,
        VersionDocumentoAdmin,
        RevisionAdmin,
        ComentarioAdmin,
        AuditoriaAdmin,
        FirmaAdmin,
        NotificacionAdmin,
        ChatMensajeAdmin,
        TenantAdmin,
        WorkflowTaskAdmin,
    ):
        admin.add_view(vista)
    return admin
