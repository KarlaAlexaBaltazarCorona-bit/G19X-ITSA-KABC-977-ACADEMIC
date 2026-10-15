"""Dependencia de FastAPI para restringir un endpoint a ciertos roles internos.

Uso típico en cualquier endpoint de negocio:

    @router.get("/inbox", dependencies=[Depends(
        requiere_roles("REVISOR_JURIDICO", "APROBADOR_JURIDICO", "ADMINISTRADOR_PLATAFORMA")
    )])
    def get_work_inbox(...):
        ...

O, si el endpoint necesita saber QUIÉN es el usuario (no solo permitir el
acceso), se usa como parámetro normal:

    def upload_document(usuario: dict = Depends(requiere_roles("REVISOR_JURIDICO", "ADMINISTRADOR_PLATAFORMA"))):
        ...
"""

from fastapi import Depends, HTTPException, status

from app.core.auth_guard import get_current_user


def requiere_roles(*roles_permitidos: str):
    """Fábrica de dependencias: retorna una dependencia que exige uno de los roles dados.

    Reproduce, ya sobre la API real, la misma matriz de "Pantalla x Rol" que
    se definió en Diseño pagina web.txt / ROLES.txt para el prototipo visual.
    """

    def verificador(usuario: dict = Depends(get_current_user)) -> dict:
        if usuario["rol"] not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Tu rol ({usuario['rol']}) no tiene permiso para acceder a este recurso. "
                    f"Roles permitidos: {', '.join(roles_permitidos)}."
                ),
            )
        return usuario

    return verificador
