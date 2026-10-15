"""Tablas ADICIONALES

Se agregan porque las piden historias de usuario ya aprobadas
(Plantilla_Historias_Usuario_xls.xlsx), pero
no tienen tabla propia en el boceto de `solicitud_r / documento / vercion_
documento / revicion / comentarios / auditoria`.

- Firma:        HU-10 (Gestionar aprobaciones) y HU-11 (Firma electrónica).
- Notificacion: HU-13 (Alertas / notificaciones).
- ChatMensaje:  (panel de chat de IA a la derecha).
"""

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text, func

from app.core.database import Base
from app.core.db_types import GUID


class EstadoFirma(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    FIRMADO = "FIRMADO"
    RECHAZADO = "RECHAZADO"


class Firma(Base):
    """Registro de firma electrónica de una solicitud ya aprobada. Tabla: `firmas` (extra)."""

    __tablename__ = "firmas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    solicitud_id = Column(GUID(), ForeignKey("solicitud_r.id"), nullable=False)
    firmante_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    estado = Column(Enum(EstadoFirma), default=EstadoFirma.PENDIENTE, nullable=False)
    # si Document Intelligence detectó una firma/sello real
    # dentro del PDF antes de marcar la solicitud como FIRMADO.
    firma_detectada_en_documento = Column(
        Enum("SI", "NO", "NO_VERIFICADO", name="firma_detectada_enum"), default="NO_VERIFICADO"
    )
    firmado_at = Column(DateTime(timezone=True), nullable=True)
    creado_at = Column(DateTime(timezone=True), server_default=func.now())


class Notificacion(Base):
    """Una alerta pendiente de leer para un usuario. Tabla: `notificaciones` (extra)."""

    __tablename__ = "notificaciones"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    solicitud_id = Column(GUID(), ForeignKey("solicitud_r.id"), nullable=True)
    titulo = Column(String, nullable=False)
    detalle = Column(String, nullable=True)
    leida = Column(Boolean, default=False, nullable=False)
    creado_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMensaje(Base):
    """Un mensaje del chat de IA sobre una solicitud. Tabla: `chat_mensajes` (extra)."""

    __tablename__ = "chat_mensajes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    solicitud_id = Column(GUID(), ForeignKey("solicitud_r.id"), nullable=False, index=True)
    autor_id = Column(GUID(), ForeignKey("users.id"), nullable=True)  # null cuando rol_mensaje == "asistente"
    rol_mensaje = Column(String, nullable=False)  # "usuario" | "asistente"
    contenido = Column(Text, nullable=False)
    creado_at = Column(DateTime(timezone=True), server_default=func.now())
