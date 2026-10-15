"""Configuración de entorno de Alembic.

A diferencia del `alembic env.py` genérico, aquí NO leemos `sqlalchemy.url`
desde `alembic.ini` (para no duplicar la cadena de conexión en dos lugares):
se toma directamente de `app.core.config.settings.POSTGRES_URL`, la misma
fuente de verdad que usa la aplicación en tiempo de ejecución.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Asegura que "app" sea importable al correr `alembic` desde la raíz del repo.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  (registra todos los modelos en Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Fuente única de verdad para la cadena de conexión: el .env de la app.
config.set_main_option("sqlalchemy.url", settings.POSTGRES_URL or "sqlite:///./legaltech_dev.db")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL de las migraciones sin conectarse a una base de datos real
    (útil para revisar el SQL antes de aplicarlo, con `alembic upgrade head --sql`).
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones conectándose de verdad a la base de datos."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
