import logging
import os
from pathlib import Path
import uuid

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.auth_guard import verify_api_key
from app.core.config import settings
from app.core.database import engine, init_db
from app.core.rate_limiter import rate_limit_guard

load_dotenv()

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

is_production = bool(os.getenv("WEBSITE_HOSTNAME")) or os.getenv("ENVIRONMENT", "").lower() == "production"
docs_enabled = settings.ENABLE_DOCS or (not is_production)

HTTP_ERROR_MESSAGES = {
    400: ("Solicitud Incorrecta", "La solicitud contiene parámetros no válidos o malformados."),
    401: ("Acceso No Autorizado", "Credenciales de acceso no proporcionadas o sesión no válida."),
    403: ("Acceso Prohibido", "No cuenta con los privilegios jurídicos necesarios para consultar este recurso."),
    404: ("Recurso No Encontrado", "El recurso al que intenta acceder no existe o fue reubicado."),
    405: ("Método No Permitido", "La operación HTTP solicitada no está permitida en este recurso."),
    413: ("Carga Útil Excesiva", "El tamaño de la petición excede el límite de seguridad permitido."),
    422: ("Error de Validación", "La estructura de los datos enviados no cumple con las reglas del sistema."),
    429: ("Límite de Peticiones Excedido", "Ha superado la tasa permitida de solicitudes. Intente nuevamente en un minuto."),
    500: ("Error Interno del Servidor", "Ocurrió una anomalía interna en el servidor."),
    502: ("Puerta de Enlace Incorrecta", "No fue posible comunicarse con los servicios de nube o Inteligencia Artificial."),
    503: ("Servicio No Disponible", "El servicio se encuentra temporalmente fuera de línea."),
}


def render_error_html(status_code: int, title: str, message: str) -> HTMLResponse:
    """Renderiza la plantilla HTML corporativa de error para usuarios que navegan desde el explorador."""
    error_file = TEMPLATES_DIR / "error.html"
    if error_file.exists():
        try:
            from jinja2 import Environment, FileSystemLoader

            env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
            template = env.get_template("error.html")
            content = template.render(code=status_code, title=title, message=message)
        except Exception as e:
            logger.error("Error al renderizar plantilla de error HTML: %s", e)
            content = f"<!DOCTYPE html><html><body style='font-family:sans-serif;text-align:center;padding:3rem'><h1>{status_code} - {title}</h1><p>{message}</p><p><a href='/login'>Volver al inicio</a></p></body></html>"
    else:
        content = f"<!DOCTYPE html><html><body><h1>{status_code} - {title}</h1><p>{message}</p></body></html>"
    return HTMLResponse(content=content, status_code=status_code)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Plataforma Inteligente para la Gestión del Workflow de Revisión Jurídica (SaaS)",
    version=settings.VERSION,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

# Configurar CORS restrictivo y seguro para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_payload_size_limit(request, call_next):
    """Mitiga ataques de DoS por buffers y payloads gigantes desde Burp Suite."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                from fastapi.responses import JSONResponse

                max_mb = settings.MAX_REQUEST_BODY_BYTES // (1024 * 1024)
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Cuerpo de la petición demasiado grande. Máximo permitido: {max_mb} MB.",
                    },
                )
        except ValueError:
            pass
    return await call_next(request)


@app.middleware("http")
async def add_security_headers_and_strip_fingerprints(request, call_next):
    """Elimina huellas del servidor (anti-fingerprinting) y añade cabeceras de seguridad OWASP."""
    response = await call_next(request)
    # Eliminar Server: uvicorn para no revelar el stack tecnológico a herramientas de escaneo
    if "server" in response.headers:
        del response.headers["server"]
    # Cabeceras estándar de protección OWASP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "connect-src 'self' https://login.microsoftonline.com https://login.live.com https://aadcdn.msauth.net https://graph.microsoft.com https://unpkg.com https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    # Optimización de caché para recursos estáticos del portal (max-age bajo para permitir despliegues continuos)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=30"
    return response


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Maneja excepciones HTTP estándar distinguiendo peticiones de navegador (HTML) y de API (JSON)."""
    # Si la excepción es una redirección HTTP (301, 302, 303, 307, 308) o tiene Location,
    # permitir que el navegador sea redirigido en vez de renderizar pantalla de error
    if exc.headers and "Location" in exc.headers:
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url=exc.headers["Location"], status_code=exc.status_code, headers=exc.headers)
    if exc.status_code in (301, 302, 303, 307, 308):
        from fastapi.responses import RedirectResponse

        loc = exc.headers.get("Location", "/login") if exc.headers else "/login"
        return RedirectResponse(url=loc, status_code=exc.status_code)

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        default_title, default_msg = HTTP_ERROR_MESSAGES.get(
            exc.status_code,
            ("Error en el Sistema", "Ocurrió un error al procesar su solicitud."),
        )
        msg = str(exc.detail) if exc.detail and exc.status_code != 404 else default_msg
        return render_error_html(exc.status_code, default_title, msg)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Sanea errores de validación de esquemas Pydantic para mitigar fuzzing y reconnaissance."""
    logger.warning("Fallo de validación en %s: %s", request.url.path, exc.errors())
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return render_error_html(
            status_code=422,
            title="Error de Validación",
            message="Los datos proporcionados no cumplen con el formato o longitud requerida.",
        )

    clean_errors = [
        {
            "loc": err.get("loc", ()),
            "msg": err.get("msg", "Error de validación"),
            "type": err.get("type", "value_error"),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": clean_errors},
    )


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    """Captura cualquier excepción no controlada generando un ID opaco de rastreo (OWASP CWE-209)."""
    tracking_id = uuid.uuid4().hex[:8]
    logger.critical(
        "Fallo no controlado [tracking_id=%s] en %s %s: %s",
        tracking_id,
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return render_error_html(
            status_code=500,
            title="Error Interno del Servidor",
            message=f"Ocurrió un error inesperado al procesar su solicitud. Código de referencia: {tracking_id}.",
        )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor.",
            "tracking_id": tracking_id,
        },
    )


# Servir recursos estáticos (JavaScript modular, hojas de estilo corporativas y assets)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Montar las rutas de la versión 1 de la API (/api/v1/...)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Montar panel administrativo (SQLAdmin) directamente sobre la aplicación
try:
    from app.admin import registrar_admin

    registrar_admin(app, engine)
    logger.info("Panel administrativo SQLAdmin montado exitosamente en /admin")
except Exception as e:
    logger.error("No se pudo montar el panel administrativo (SQLAdmin): %s", e)


@app.on_event("startup")
def _inicializar_recursos_al_arrancar() -> None:
    """Crea las tablas que falten (red de seguridad de desarrollo, ver init_db())."""
    try:
        init_db()
    except Exception as e:
        logger.error("Aviso: No se pudo conectar a la base de datos durante startup (posible timeout de red o Azure): %s", e)


@app.get("/")
def read_root(request: Request):
    """Punto de entrada: redirige al dashboard si hay sesión activa o a /login si no."""
    if "text/html" in request.headers.get("accept", ""):
        from fastapi.responses import RedirectResponse

        token = request.cookies.get("plurione_auth_token") or request.cookies.get("access_token")
        if token:
            return RedirectResponse(url="/api/v1/app/dashboard", status_code=307)
        return RedirectResponse(url="/login", status_code=307)
    return {"status": "online"}


@app.get("/login", summary="Pantalla de Acceso Microsoft Entra ID", include_in_schema=False)
def login_view():
    """Sirve directamente la pantalla de inicio de sesión institucional."""
    from app.api.v1.endpoints.auth import get_login_page

    return get_login_page()


@app.get("/logout", summary="Cerrar sesión y redirigir", include_in_schema=False)
def logout_view():
    """Limpia la sesión y redirige a /login."""
    from fastapi.responses import RedirectResponse

    res = RedirectResponse(url="/login", status_code=307)
    res.delete_cookie(key="plurione_auth_token", path="/")
    res.delete_cookie(key="access_token", path="/")
    return res


@app.get("/app/{full_path:path}", include_in_schema=False)
def redirect_app_path(full_path: str):
    """Redirige rutas legacy /app/... a /api/v1/app/..."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"/api/v1/app/{full_path}", status_code=307)


@app.get("/health")
def health_check():
    """Sonda de salud requerida por Azure App Service (sin exponer metadatos del entorno)."""
    return {"status": "healthy"}


@app.get("/api/info", dependencies=[Depends(verify_api_key), Depends(rate_limit_guard)])
def get_info():
    """Verificación de estado operativo de la API (requiere API Key)."""
    return {"status": "operational"}

