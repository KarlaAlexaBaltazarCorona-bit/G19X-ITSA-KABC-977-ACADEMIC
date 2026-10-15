"""Modelos iniciales: users, solicitud_r, documento, vercion_documento,
revicion, comentarios, auditoria + tablas extra (firmas, notificaciones,
chat_mensajes).

Revision ID: 0001
Revises: --
Create Date: 2026-09-17
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tipo UUID portable: en Postgres usa el tipo nativo; en SQLite (solo desarrollo)
# usa CHAR(36). Se decide en tiempo de ejecución a partir del dialecto activo.
def _uuid_col(name: str, **kw):
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kw)


def upgrade() -> None:
    # ------------------------------------------------------------------ users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("objeto_id", sa.String(), nullable=False, unique=True),
        sa.Column("correo", sa.String(), nullable=False, unique=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("apellido", sa.String(), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "SOLICITANTE",
                "REVISOR_JURIDICO",
                "APROBADOR_JURIDICO",
                "ADMINISTRADOR_PLATAFORMA",
                "AUDITOR",
                name="rolusuario",
            ),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ultima_vez", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actualizado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_correo", "users", ["correo"])
    op.create_index("ix_users_objeto_id", "users", ["objeto_id"])

    # ------------------------------------------------------------ solicitud_r
    op.create_table(
        "solicitud_r",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero_respuesta", sa.String(), nullable=True, unique=True),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("requested_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("revicion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("tipo_documento", sa.String(), nullable=False),
        sa.Column(
            "prioridad",
            sa.Enum("BAJA", "NORMAL", "ALTA", "URGENTE", name="prioridadsolicitud"),
            nullable=False,
            server_default="NORMAL",
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "BORRADOR", "EN_REVISION", "OBSERVADO", "EN_APROBACION",
                "APROBADO", "RECHAZADO", "FIRMADO",
                name="estadosolicitud",
            ),
            nullable=False,
            server_default="BORRADOR",
        ),
        sa.Column("fecha_limite", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actualizado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finalizo_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_solicitud_r_estado", "solicitud_r", ["estado"])

    # ------------------------------------------------------------- documento
    op.create_table(
        "documento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solicitud_r.id"), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("tipo_documento", sa.String(), nullable=False),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actualizado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -------------------------------------------------------- vercion_documento
    op.create_table(
        "vercion_documento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documento.id"), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False),
        sa.Column("nombre_archivo", sa.String(), nullable=False),
        sa.Column("ubicacion", sa.String(), nullable=False),
        sa.Column("tamano_archivo", sa.Integer(), nullable=True),
        sa.Column("formato_archivo", sa.String(), nullable=True),
        sa.Column("hash_contenido", sa.String(), nullable=True),
        sa.Column("actualizado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vercion_documento_hash", "vercion_documento", ["hash_contenido"])

    # --------------------------------------------------------------- revicion
    op.create_table(
        "revicion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solicitud_r.id"), nullable=False),
        sa.Column("revizado_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("vercion_documento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vercion_documento.id"), nullable=False),
        sa.Column(
            "estado",
            sa.Enum("PENDIENTE", "EN_PROGRESO", "COMPLETADA", name="estadorevision"),
            nullable=False,
            server_default="PENDIENTE",
        ),
        sa.Column(
            "decision",
            sa.Enum("SIN_DECISION", "APROBAR", "SOLICITAR_CAMBIOS", "RECHAZAR", name="decisionrevision"),
            nullable=False,
            server_default="SIN_DECISION",
        ),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("empezado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completado_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------ comentarios
    op.create_table(
        "comentarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solicitud_r.id"), nullable=False),
        sa.Column("vercion_documento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vercion_documento.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("comentario_padre_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("comentarios.id"), nullable=True),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("resuelto", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actualizado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resuelto_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -------------------------------------------------------------- auditoria
    op.create_table(
        "auditoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solicitud_r.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tipo_documento", sa.String(), nullable=False),
        sa.Column("id_documento", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accion", sa.String(), nullable=False),
        sa.Column("valor_anterior", sa.Text(), nullable=True),
        sa.Column("valor_nuevo", sa.Text(), nullable=True),
        sa.Column("direccion_ip", sa.String(), nullable=True),
        sa.Column("usuario_buscador", sa.String(), nullable=True),
        sa.Column("creada_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_auditoria_solicitud", "auditoria", ["solicitud_id"])

    # ---- Tablas extra (fuera del ER original -- ver app/models/extras.py) ----

    # ----------------------------------------------------------------- firmas
    op.create_table(
        "firmas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solicitud_r.id"), nullable=False),
        sa.Column("firmante_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "estado",
            sa.Enum("PENDIENTE", "FIRMADO", "RECHAZADO", name="estadofirma"),
            nullable=False,
            server_default="PENDIENTE",
        ),
        sa.Column(
            "firma_detectada_en_documento",
            sa.Enum("SI", "NO", "NO_VERIFICADO", name="firma_detectada_enum"),
            server_default="NO_VERIFICADO",
        ),
        sa.Column("firmado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -------------------------------------------------------- notificaciones
    op.create_table(
        "notificaciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solicitud_r.id"), nullable=True),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("detalle", sa.String(), nullable=True),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --------------------------------------------------------- chat_mensajes
    op.create_table(
        "chat_mensajes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solicitud_r.id"), nullable=False),
        sa.Column("autor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rol_mensaje", sa.String(), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_solicitud", "chat_mensajes", ["solicitud_id"])

    # ---- Tablas de modelos conservados del repo original ----

    # ---------------------------------------------------------------- tenants
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre_comercial", sa.String(), nullable=False),
        sa.Column("rfc", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # ---------------------------------------------------------- workflow_tasks
    op.create_table(
        "workflow_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solicitud_r.id"), nullable=False),
        sa.Column("revisor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("etapa", sa.String(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum("PENDIENTE", "EN_PROGRESO", "COMPLETADA", name="estadotarea"),
            nullable=False,
            server_default="PENDIENTE",
        ),
        sa.Column("fecha_limite", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("chat_mensajes")
    op.drop_table("notificaciones")
    op.drop_table("firmas")
    op.drop_table("workflow_tasks")
    op.drop_table("tenants")
    op.drop_table("auditoria")
    op.drop_table("comentarios")
    op.drop_table("revicion")
    op.drop_table("vercion_documento")
    op.drop_table("documento")
    op.drop_table("solicitud_r")
    op.drop_table("users")

    # Eliminar los tipos Enum de Postgres (no existen en SQLite)
    for enum_name in (
        "rolusuario", "prioridadsolicitud", "estadosolicitud",
        "estadorevision", "decisionrevision", "estadofirma", "firma_detectada_enum",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
