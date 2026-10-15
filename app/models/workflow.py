"""Modelo de Tarea de Workflow.

Esta tabla (`workflow_tasks`) se deja disponible para flujos futuros donde se
necesite un seguimiento de tareas más granular (por ejemplo, tareas paralelas
dentro de una misma solicitud) sin romper la arquitectura actual.
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, func

from app.core.database import Base
from app.core.db_types import GUID


class EstadoTarea(str, enum.Enum):
    """Estado de avance de una tarea de workflow."""

    PENDIENTE = "PENDIENTE"
    EN_PROGRESO = "EN_PROGRESO"
    COMPLETADA = "COMPLETADA"


class WorkflowTaskModel(Base):
    """Tarea de workflow asignada a un usuario. Tabla: `workflow_tasks`.

    Compatible con el nombre del cascarón original (`WorkflowTaskModel`)
    para no romper imports existentes.
    """

    __tablename__ = "workflow_tasks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID(), ForeignKey("solicitud_r.id"), nullable=False)
    revisor_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    etapa = Column(String, nullable=False)  # "revision" | "aprobacion" | "firma"
    estado = Column(Enum(EstadoTarea), default=EstadoTarea.PENDIENTE, nullable=False)
    fecha_limite = Column(DateTime(timezone=True), nullable=True)
    creado_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WorkflowTaskModel etapa={self.etapa!r} estado={self.estado}>"
