# ═════════════════════════════════════════════════════════════════════════════
# Dockerfile — LegalTech Workflow API (Producción & Contenedores)
# Cumple requerimientos del Proyecto de Desarrollo (Sección 2: Docker)
# ═════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim as base

# Variables de entorno de Python para producción
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace \
    PORT=8000

# Instalar dependencias del sistema mínimas requeridas (curl para healthcheck, libpq para postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Crear usuario sin privilegios para ejecución segura (OWASP / Bandit compliance)
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Copiar el código fuente de la aplicación
COPY app/ ./app/
COPY main.py .
COPY pyproject.toml .
COPY alembic.ini .

# Ajustar permisos para el usuario no privilegiado
RUN chown -R appuser:appgroup /workspace

USER appuser

# Exponer el puerto del servicio
EXPOSE 8000

# Sonda de salud (Healthcheck) nativa de Docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de arranque con servidor ASGI de alto rendimiento
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
