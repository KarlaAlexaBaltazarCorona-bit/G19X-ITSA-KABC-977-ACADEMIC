"""Módulo de Gestión de Usuarios y Funcionarios (tabla `users`).

Permite al ADMINISTRADOR_PLATAFORMA listar, crear, editar roles y activar/desactivar
a los colaboradores del sistema judicial / legaltech (Pantalla 13).
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.audit_helper import registrar_auditoria
from app.core.database import get_db
from app.core.roles_guard import requiere_roles
from app.models.user import RolUsuario, Usuario
from app.schemas.user import UsuarioCreate, UsuarioResponse, UsuarioUpdate

router = APIRouter()

ROL_ADMIN = (RolUsuario.ADMINISTRADOR_PLATAFORMA.value,)


@router.get(
    "/",
    response_model=list[UsuarioResponse],
    summary="Listar todos los usuarios del sistema",
    dependencies=[Depends(requiere_roles(*ROL_ADMIN))],
)
def listar_usuarios(db: Session = Depends(get_db)):
    """Devuelve la lista completa de colaboradores y funcionarios registrados."""
    return db.query(Usuario).order_by(Usuario.nombre.asc()).all()


@router.get(
    "/{user_id}",
    response_model=UsuarioResponse,
    summary="Obtener detalle de un usuario",
    dependencies=[Depends(requiere_roles(*ROL_ADMIN))],
)
def obtener_usuario(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Obtiene los datos de un usuario por su identificador UUID."""
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return user


@router.post(
    "/",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pre-registrar un nuevo colaborador o funcionario",
)
def crear_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    usuario_admin: dict = Depends(requiere_roles(*ROL_ADMIN)),
    request: Request = None,
):
    """Registra a un nuevo funcionario con su correo y rol antes de su primer inicio de sesión."""
    correo_limpio = payload.correo.strip().lower()
    existente = db.query(Usuario).filter(Usuario.correo == correo_limpio).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario registrado con el correo {correo_limpio}.",
        )

    objeto_id = payload.objeto_id or f"pending-{correo_limpio}"
    nuevo_usuario = Usuario(
        objeto_id=objeto_id,
        correo=correo_limpio,
        nombre=payload.nombre.strip(),
        apellido=payload.apellido.strip() if payload.apellido else None,
        role=payload.role,
        activo=True,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    registrar_auditoria(
        db,
        usuario_admin,
        accion=f"Pre-registró al usuario {nuevo_usuario.nombre_completo} con rol {nuevo_usuario.role.value}.",
        tipo_documento="usuario",
        id_documento=nuevo_usuario.id,
        request=request,
    )
    return nuevo_usuario


@router.put(
    "/{user_id}",
    response_model=UsuarioResponse,
    summary="Actualizar un usuario (rol, estado, nombre)",
)
def actualizar_usuario(
    user_id: uuid.UUID,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_admin: dict = Depends(requiere_roles(*ROL_ADMIN)),
    request: Request = None,
):
    """Permite al administrador modificar el rol, estado de activación y datos de un funcionario."""
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    cambios = []
    if payload.nombre is not None:
        user.nombre = payload.nombre.strip()
        cambios.append("nombre")
    if payload.apellido is not None:
        user.apellido = payload.apellido.strip() if payload.apellido else None
        cambios.append("apellido")
    if payload.role is not None and user.role != payload.role:
        cambios.append(f"rol: {user.role.value} -> {payload.role.value}")
        user.role = payload.role
    if payload.activo is not None and user.activo != payload.activo:
        cambios.append(f"activo: {user.activo} -> {payload.activo}")
        user.activo = payload.activo

    db.commit()
    db.refresh(user)

    if cambios:
        registrar_auditoria(
            db,
            usuario_admin,
            accion=f"Actualizó usuario {user.correo}: {', '.join(cambios)}.",
            tipo_documento="usuario",
            id_documento=user.id,
            request=request,
        )

    return user


@router.delete(
    "/{user_id}",
    response_model=UsuarioResponse,
    summary="Desactivar a un funcionario",
)
def desactivar_usuario(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario_admin: dict = Depends(requiere_roles(*ROL_ADMIN)),
    request: Request = None,
):
    """Desactiva el acceso de un usuario a la plataforma sin borrar el historial de auditoría."""
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    user.activo = False
    db.commit()
    db.refresh(user)

    registrar_auditoria(
        db,
        usuario_admin,
        accion=f"Desactivó la cuenta del usuario {user.correo}.",
        tipo_documento="usuario",
        id_documento=user.id,
        request=request,
    )
    return user
