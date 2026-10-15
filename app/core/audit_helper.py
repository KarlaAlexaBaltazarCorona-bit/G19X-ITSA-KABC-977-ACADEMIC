"""Helper único para registrar auditoría.

Regla de equipo: NINGÚN endpoint que cambie algo (crear solicitud, comentar,
reasignar, revisar, firmar...) se aprueba en code review si no llama a
`registrar_auditoria(...)`. Centralizarlo evita que cada quien tenga que
acordarse a mano de fecha/hora/usuario/IP en cada endpoint -- ver HU-12.

La tabla `auditoria` (app/models/audit.py) es GENÉRICA: no solo audita
documentos, audita cualquier entidad del sistema a través de
`tipo_documento` (el tipo de entidad, p. ej. "solicitud", "comentario",
"revision") + `id_documento` (el id de esa entidad).
"""

import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import Auditoria


def registrar_auditoria(
    db: Session,
    usuario: dict,
    accion: str,
    tipo_documento: str,
    id_documento: uuid.UUID | str | None = None,
    solicitud_id: uuid.UUID | str | None = None,
    valor_anterior: str | None = None,
    valor_nuevo: str | None = None,
    request: Request | None = None,
) -> Auditoria:
    """Inserta una fila de auditoría.

    Parámetros:
    - `usuario`: el dict que retorna `get_current_user` (necesita al menos `usuario["id"]`).
    - `accion`: descripción corta y legible de lo que pasó, p. ej. "Aprobó la solicitud".
    - `tipo_documento`: qué TIPO de entidad se modificó ("solicitud", "documento",
      "comentario", "revision", "firma", "usuario"...).
    - `id_documento`: el id de esa entidad específica.
    - `solicitud_id`: a qué Solicitud_R pertenece el cambio (para poder listar
      "toda la trazabilidad de esta solicitud" en un solo query -- HU-12).
    - `valor_anterior` / `valor_nuevo`: opcional, para dejar rastro de qué
      cambió exactamente (p. ej. estado anterior -> estado nuevo).
    - `request`: si se pasa el `Request` de FastAPI, se capturan automáticamente
      `direccion_ip` y `usuario_buscador` (User-Agent) sin que cada endpoint
      tenga que extraerlos a mano.
    """
    direccion_ip = None
    usuario_buscador = None
    if request is not None:
        direccion_ip = request.client.host if request.client else None
        usuario_buscador = request.headers.get("user-agent")

    registro = Auditoria(
        solicitud_id=solicitud_id,
        user_id=usuario["id"],
        tipo_documento=tipo_documento,
        id_documento=id_documento,
        accion=accion,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        direccion_ip=direccion_ip,
        usuario_buscador=usuario_buscador,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro
