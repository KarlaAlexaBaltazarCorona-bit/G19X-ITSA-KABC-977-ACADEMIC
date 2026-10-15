"""Motor BPM: asignación automática, versionado y transición de estados.

Reemplaza el cascarón original (`assign_reviewer` que siempre regresaba el
mismo texto fijo) con reglas reales sobre la base de datos. Ahora opera sobre
`SolicitudRevision` (tabla `solicitud_r`), que es el nodo central del ER real
del equipo -- no sobre `Documento` directamente, ya que un documento por sí
solo no tiene revisor asignado; su Solicitud_R sí.

Cubre HU-03 (asignación automática), HU-08/HU-09 (versionado) y las transiciones de estado de HU-05/HU-09/HU-10.
"""

import hashlib
import logging

from sqlalchemy.orm import Session

from app.core.audit_helper import registrar_auditoria
from app.models.document import Documento
from app.models.solicitud import EstadoSolicitud, SolicitudRevision
from app.models.user import RolUsuario, Usuario
from app.models.version import VersionDocumento
from app.services.azure_blob import AzureBlobService

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Orquesta el recorrido de una Solicitud de Revisión a través del workflow."""

    @staticmethod
    def generar_folio_expediente(db: Session) -> str:
        """Genera un folio consecutivo único con formato EXP-YYYY-XXXX (RF-002, HU-01)."""
        import datetime as _dt

        anio = _dt.datetime.now(_dt.UTC).year
        prefijo = f"EXP-{anio}-"
        ultima_solicitud = (
            db.query(SolicitudRevision)
            .filter(SolicitudRevision.numero_respuesta.like(f"{prefijo}%"))
            .order_by(SolicitudRevision.numero_respuesta.desc())
            .first()
        )
        if ultima_solicitud and ultima_solicitud.numero_respuesta:
            try:
                consecutivo = int(ultima_solicitud.numero_respuesta.split("-")[-1]) + 1
            except ValueError:
                consecutivo = 1
        else:
            total = db.query(SolicitudRevision).count()
            consecutivo = total + 1

        return f"{prefijo}{consecutivo:04d}"

    @staticmethod
    def assign_reviewer(db: Session) -> Usuario:
        """Asigna automáticamente al Revisor Jurídico con menos carga de trabajo activa.

        Regla de negocio (round-robin por carga, HU-03): entre todos los
        usuarios con `role == REVISOR_JURIDICO` y `activo=True`, se elige al
        que tenga menos solicitudes activas (no BORRADOR, APROBADO, RECHAZADO
        ni FIRMADO) asignadas en `solicitud_r.revicion_id`.
        """
        revisores = (
            db.query(Usuario).filter(Usuario.role == RolUsuario.REVISOR_JURIDICO, Usuario.activo == True).all()  # noqa: E712
        )
        if not revisores:
            raise ValueError(
                "No hay revisores jurídicos activos disponibles. Registra al menos uno "
                "desde la Pantalla 13 (Usuarios y funcionarios) antes de asignar solicitudes."
            )

        estados_activos = (
            EstadoSolicitud.EN_REVISION,
            EstadoSolicitud.OBSERVADO,
            EstadoSolicitud.EN_APROBACION,
        )
        carga_por_revisor = {
            revisor.id: db.query(SolicitudRevision)
            .filter(
                SolicitudRevision.revicion_id == revisor.id,
                SolicitudRevision.estado.in_(estados_activos),
            )
            .count()
            for revisor in revisores
        }
        id_revisor_elegido = min(carga_por_revisor, key=carga_por_revisor.get)
        return next(r for r in revisores if r.id == id_revisor_elegido)

    @staticmethod
    def iniciar_revision(db: Session, solicitud: SolicitudRevision, usuario: dict, request=None) -> SolicitudRevision:
        """Asigna revisor automáticamente a una solicitud recién creada y la pasa a EN_REVISION."""
        revisor = WorkflowEngine.assign_reviewer(db)
        solicitud.revicion_id = revisor.id
        solicitud.estado = EstadoSolicitud.EN_REVISION
        db.commit()
        db.refresh(solicitud)

        registrar_auditoria(
            db,
            usuario,
            accion=f"Asignó automáticamente la solicitud a {revisor.nombre_completo} para revisión.",
            tipo_documento="solicitud",
            id_documento=solicitud.id,
            solicitud_id=solicitud.id,
            valor_nuevo=EstadoSolicitud.EN_REVISION.value,
            request=request,
        )
        return solicitud

    @staticmethod
    def reasignar_revisor(db: Session, solicitud: SolicitudRevision, nuevo_revisor_id, usuario: dict, request=None):
        """Reasignación manual por el Admin (observación 15.1) cuando el balanceo automático no aplica."""
        anterior = str(solicitud.revicion_id) if solicitud.revicion_id else None
        solicitud.revicion_id = nuevo_revisor_id
        db.commit()
        db.refresh(solicitud)
        registrar_auditoria(
            db,
            usuario,
            accion="Reasignó manualmente el revisor de la solicitud.",
            tipo_documento="solicitud",
            id_documento=solicitud.id,
            solicitud_id=solicitud.id,
            valor_anterior=anterior,
            valor_nuevo=str(nuevo_revisor_id),
            request=request,
        )
        return solicitud

    @staticmethod
    def guardar_version_si_cambio(
        db: Session,
        documento: Documento,
        contenido: bytes,
        nombre_archivo: str,
        formato_archivo: str,
        usuario: dict,
        request=None,
    ) -> VersionDocumento:
        """Crea una versión nueva de un `Documento` SOLO si el contenido realmente cambió.

        Resuelve("que cuando un documento se abra se
        guarden las modificaciones, para llevar control de versiones"):
        compara el hash SHA-256 del contenido nuevo contra el de la última
        versión guardada. Si es igual, no duplica versión.
        """
        nuevo_hash = hashlib.sha256(contenido).hexdigest()
        ultima_version = (
            db.query(VersionDocumento)
            .filter(VersionDocumento.documento_id == documento.id)
            .order_by(VersionDocumento.numero_version.desc())
            .first()
        )
        if ultima_version and ultima_version.hash_contenido == nuevo_hash:
            logger.info("El contenido de %s no cambió; no se crea una versión nueva.", documento.id)
            return ultima_version

        siguiente_numero = (ultima_version.numero_version + 1) if ultima_version else 1
        nombre_blob = f"{documento.id}-v{siguiente_numero}-{nombre_archivo}"
        ubicacion = AzureBlobService.upload_file(nombre_blob, contenido)

        version = VersionDocumento(
            documento_id=documento.id,
            numero_version=siguiente_numero,
            nombre_archivo=nombre_archivo,
            ubicacion=ubicacion,
            tamano_archivo=len(contenido),
            formato_archivo=formato_archivo,
            hash_contenido=nuevo_hash,
            actualizado_por=usuario["id"],
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        registrar_auditoria(
            db,
            usuario,
            accion=f"Guardó la versión {siguiente_numero} de {nombre_archivo}.",
            tipo_documento="documento",
            id_documento=documento.id,
            solicitud_id=documento.solicitud_id,
            request=request,
        )
        return version

    @staticmethod
    def transicionar_estado(
        db: Session,
        solicitud: SolicitudRevision,
        nuevo_estado: EstadoSolicitud,
        usuario: dict,
        motivo: str | None = None,
        request=None,
    ) -> SolicitudRevision:
        """Cambia el estado de una solicitud y deja rastro en la auditoría (HU-05, HU-09, HU-10)."""
        estado_anterior = solicitud.estado
        solicitud.estado = nuevo_estado
        if nuevo_estado in (EstadoSolicitud.APROBADO, EstadoSolicitud.RECHAZADO, EstadoSolicitud.FIRMADO):
            import datetime as _dt

            solicitud.finalizo_at = _dt.datetime.now(_dt.UTC)
        db.commit()
        db.refresh(solicitud)

        detalle_motivo = f" Motivo: {motivo}" if motivo else ""
        registrar_auditoria(
            db,
            usuario,
            accion=f"Cambió el estado de la solicitud.{detalle_motivo}",
            tipo_documento="solicitud",
            id_documento=solicitud.id,
            solicitud_id=solicitud.id,
            valor_anterior=estado_anterior.value,
            valor_nuevo=nuevo_estado.value,
            request=request,
        )
        return solicitud
