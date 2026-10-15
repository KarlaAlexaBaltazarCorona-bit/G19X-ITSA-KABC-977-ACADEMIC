"""Limitador de tasa de peticiones en memoria (Anti-Abuso y Anti-Bruteforce / Burp Intruder)."""

import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, Request, status
from app.core.config import settings


class InMemoryRateLimiter:
    """Implementa una ventana deslizante en memoria por cliente / colaborador."""

    def __init__(self, max_requests: int = 2400, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, client_id: str) -> None:
        """Verifica si el cliente/colaborador ha excedido la tasa máxima permitida."""
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return

        now = time.time()
        effective_limit = getattr(settings, "RATE_LIMIT_PER_MINUTE", self.max_requests)
        with self._lock:
            timestamps = self._requests[client_id]
            cutoff = now - self.window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]
            self._requests[client_id] = valid_timestamps

            if len(valid_timestamps) >= effective_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Límite de peticiones excedido ({effective_limit} peticiones por minuto). "
                        "Por favor espere antes de enviar nuevas solicitudes."
                    ),
                    headers={"Retry-After": str(self.window_seconds)},
                )

            self._requests[client_id].append(now)


rate_limiter = InMemoryRateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)


def get_client_identifier(request: Request) -> str:
    """Obtiene un identificador único por colaborador o IP real (compatible con Azure y proxies)."""
    # 1. Sesión explícita de colaborador enviada desde el frontend
    client_session = request.headers.get("x-client-session-id")
    if client_session and len(client_session) >= 8:
        return f"sess:{client_session[:32]}"

    # 2. Si el usuario está autenticado por token, usamos un identificador por usuario
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if len(token) > 16:
            return f"user:{token[:16]}"

    cookie_token = request.cookies.get("plurione_auth_token") or request.cookies.get("access_token")
    if cookie_token and len(cookie_token) > 16:
        return f"user:{cookie_token[:16]}"

    # 3. Si se utiliza API Key corporativa o servicio
    api_key = request.headers.get("x-api-key")
    if api_key and len(api_key) >= 16:
        return f"key:{api_key[:16]}"

    # 4. Si viene detrás de Azure App Service / Cloudflare / Proxy inverso, usar X-Forwarded-For
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()

    return request.client.host if request.client else "unknown"


def rate_limit_guard(request: Request) -> None:
    """Dependencia de FastAPI para proteger endpoints asegurando cuota individual para colaboradores."""
    # Exentar rutas de polling ligero o solo lectura frecuente para no castigar al usuario
    path = request.url.path
    if request.method == "GET" and ("/notifications/pending" in path or "/chat/" in path):
        return

    client_id = get_client_identifier(request)
    rate_limiter.check(client_id)


