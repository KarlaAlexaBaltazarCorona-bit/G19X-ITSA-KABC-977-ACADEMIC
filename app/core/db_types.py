"""Tipos de columna SQLAlchemy compartidos por todos los modelos.

Separado en su propio módulo (en vez de vivir dentro de un modelo cualquiera)
para que cualquier archivo en app/models/ pueda importarlo sin depender de
otro modelo.
"""

import uuid

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Tipo UUID portable entre PostgreSQL (nativo) y SQLite (texto).

    El backend "oficial" del proyecto es PostgreSQL (ver app/core/database.py),
    pero mientras cada quien monta su Postgres local, el sistema puede correr
    sobre SQLite para desarrollo/pruebas. Este tipo hace que los modelos no
    tengan que preocuparse por esa diferencia: en Postgres usa el tipo UUID
    nativo, en SQLite lo guarda como texto de 36 caracteres.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
