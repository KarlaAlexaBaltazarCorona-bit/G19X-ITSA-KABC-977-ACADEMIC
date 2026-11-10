"""Configuración del motor SQLAlchemy y de las sesiones de base de datos.

Este módulo es el único punto donde se crea el `engine` y la fábrica de
sesiones (`SessionLocal`). Todo lo demás (modelos, endpoints, Alembic)
importa `Base`, `engine` o `get_db` desde aquí para no duplicar configuración.

Notas de diseño:
- Si `POSTGRES_URL` no está definida en el `.env`,
  caemos automáticamente a un archivo SQLite local (`legaltech_dev.db`).
  Esto permite programar y correr las pruebas sin bloquear a nadie mientras
  se resuelve la base de datos "oficial" del equipo. En producción SIEMPRE
  debe existir `POSTGRES_URL` apuntando a Azure Database for PostgreSQL.
- `Alembic` es la fuente de verdad para la evolución del esquema (crear
  columnas, índices, etc.). `init_db()` solo crea las tablas que falten como
  red de seguridad para desarrollo local; nunca reemplaza a las migraciones.
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Resolución de la cadena de conexión -----------------------------------
# En producción (Azure) esto SIEMPRE debe venir de POSTGRES_URL.
SQLALCHEMY_DATABASE_URL = settings.POSTGRES_URL or "sqlite:///./legaltech_dev.db"

# Normalizar prefijo para garantizar el uso del driver psycopg2 instalado
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
elif SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    logger.warning(
        "POSTGRES_URL no está configurada: usando SQLite local (%s) solo para "
        "desarrollo/pruebas. Configura POSTGRES_URL antes de desplegar a producción.",
        SQLALCHEMY_DATABASE_URL,
    )
    # SQLite exige este flag cuando la misma conexión se comparte entre hilos
    # (FastAPI puede atender peticiones en hilos distintos).
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping evita el típico error "server closed the connection unexpectedly"
    # cuando Azure recicla conexiones inactivas.
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base declarativa: todos los modelos en app/models heredan de aquí."""


def get_db():
    """Dependencia de FastAPI: entrega una sesión de BD y la cierra al terminar la petición.

    Uso en un endpoint:
        def mi_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea las tablas que falten según los modelos registrados en `Base.metadata`.

    Se llama una vez al iniciar la aplicación (ver app/main.py). Es idempotente:
    si las tablas ya existen (por ejemplo, porque Alembic ya corrió en
    producción) no hace nada. NO reemplaza a `alembic upgrade head`.
    """
    # Importar los modelos aquí (no arriba) evita import circular: los modelos
    # importan `Base` de este mismo archivo.
    from app.models import (  # noqa: F401  (el import registra las tablas en Base.metadata)
        audit,
        comment,
        document,
        extras,
        revision,
        solicitud,
        tenant,
        user,
        version,
        workflow,
    )

    Base.metadata.create_all(bind=engine)
    seed_initial_admin()


def seed_initial_admin() -> None:
    """Inicializa de manera idempotente la cuenta administradora inicial de la plataforma."""
    from app.core.config import settings
    from app.models.user import RolUsuario, Usuario

    db = SessionLocal()
    try:
        raw_admin_correos = (getattr(settings, "INITIAL_ADMIN_EMAIL", None) or "").strip()
        admin_correos = [c.strip().lower() for c in raw_admin_correos.split(",") if c.strip()]
        if not admin_correos:
            return

        for correo in admin_correos:
            admin_user = db.query(Usuario).filter(Usuario.correo == correo).first()
            if not admin_user:
                admin_user = Usuario(
                    objeto_id=f"pending-{correo}",
                    correo=correo,
                    nombre="Administrador",
                    apellido="del Sistema",
                    role=RolUsuario.ADMINISTRADOR_PLATAFORMA,
                    activo=True,
                )
                db.add(admin_user)
            elif admin_user.role != RolUsuario.ADMINISTRADOR_PLATAFORMA:
                admin_user.role = RolUsuario.ADMINISTRADOR_PLATAFORMA

        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("No se pudo pre-sembrar la cuenta administradora inicial: %s", e)
    finally:
        db.close()
