"""Esquemas de validación Pydantic para Usuarios internos (tabla `users`)."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import RolUsuario


class UsuarioResponse(BaseModel):
    """Datos públicos de un usuario interno (sin campos sensibles)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    correo: str
    nombre: str
    apellido: str | None = None
    role: RolUsuario
    activo: bool


class UsuarioCreate(BaseModel):
    """Esquema de entrada para pre-registrar a un funcionario (Pantalla 13)."""

    nombre: str = Field(..., min_length=1, max_length=150)
    apellido: str | None = Field(default=None, max_length=150)
    correo: EmailStr
    role: RolUsuario
    # Se pide para poder pre-registrar al usuario ANTES de su primer login con
    # Entra ID; cuando esa persona entre por primera vez, el sistema empata su
    # "objeto_id" real con este registro por correo (ver get_or_create_usuario).
    objeto_id: str | None = None


class UsuarioUpdate(BaseModel):
    """Esquema para actualizar datos de un usuario por el administrador."""

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    apellido: str | None = Field(default=None, max_length=150)
    role: RolUsuario | None = None
    activo: bool | None = None
