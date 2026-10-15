"""Pruebas del helper de auditoría y del endpoint de trazabilidad."""

import uuid

from sqlalchemy.orm import Session

from app.core.audit_helper import registrar_auditoria
from app.models.audit import Auditoria


def test_registrar_auditoria_crea_fila(db: Session):
    """La función `registrar_auditoria` debe crear una fila en la tabla `auditoria`."""
    # Creamos un usuario de prueba mínimo para satisfacer la FK
    from app.models.user import RolUsuario, Usuario

    usuario_db = Usuario(
        id=uuid.uuid4(),
        objeto_id="test-oid-audit",
        correo="auditor@test.local",
        nombre="Auditor",
        role=RolUsuario.AUDITOR,
    )
    db.add(usuario_db)
    db.commit()

    usuario_dict = {"id": str(usuario_db.id), "nombre": "Auditor", "correo": "auditor@test.local", "rol": "AUDITOR", "activo": True}

    registro = registrar_auditoria(
        db,
        usuario_dict,
        accion="Prueba de auditoría",
        tipo_documento="test",
        id_documento=uuid.uuid4(),
    )

    assert registro.id is not None
    assert registro.accion == "Prueba de auditoría"
    assert registro.tipo_documento == "test"
    assert db.query(Auditoria).filter(Auditoria.id == registro.id).count() == 1
