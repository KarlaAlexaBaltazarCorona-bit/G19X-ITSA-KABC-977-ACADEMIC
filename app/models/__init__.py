"""Registro central de modelos SQLAlchemy.

Importar este paquete garantiza que todas las clases de modelo queden
registradas en `Base.metadata`, necesario para Alembic (`--autogenerate`) y
para `init_db()` (app/core/database.py).

Orden de la lista = orden aproximado de dependencia (de padres a hijos) tal
como quedó en el ER del equipo: users -> solicitud_r -> documento ->
vercion_documento -> revicion / comentarios / auditoria -> extras.
"""

from app.models import audit, comment, document, extras, revision, solicitud, tenant, user, version, workflow  # noqa: F401
