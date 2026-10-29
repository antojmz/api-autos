"""
dependencies.py — Inyección de dependencias de api-usuarios.

Además de la sesión y la paginación (igual que en api-autos), aquí están los
"guards" de autenticación:

  obtener_usuario_actual  -> exige un token válido Y que el usuario siga
                             existiendo y activo en la BD (401 si no).
  requiere_admin          -> además exige rol admin (403 si no).

Diferencia con api-autos: allí basta con validar el token (stateless). Aquí,
como tenemos la tabla de usuarios, comprobamos también la BD en cada petición:
si un admin desactiva a un usuario, su token deja de servir en este servicio
al instante, aunque no haya expirado.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from auth_jwt import Rol, TokenInvalido, decodificar_token, error_401
from app.database import get_session
from app.models import Usuario

LIMITE_MAXIMO_PAGINA = 100

SessionDep = Annotated[Session, Depends(get_session)]


@dataclass(frozen=True)
class Paginacion:
    skip: int
    limit: int


def parametros_paginacion(
    skip: Annotated[int, Query(ge=0, description="Registros a saltar")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=LIMITE_MAXIMO_PAGINA, description="Máximo de registros")
    ] = 10,
) -> Paginacion:
    return Paginacion(skip=skip, limit=limit)


PaginacionDep = Annotated[Paginacion, Depends(parametros_paginacion)]

# OAuth2PasswordBearer lee la cabecera "Authorization: Bearer <token>".
# `tokenUrl` indica a Swagger UI dónde hacer login: el botón "Authorize" de
# /docs pedirá usuario y contraseña y obtendrá el token automáticamente.
# auto_error=False: devolvemos nosotros el 401 con nuestro formato.
esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def obtener_usuario_actual(
    token: Annotated[str | None, Depends(esquema_oauth2)],
    session: SessionDep,
) -> Usuario:
    if token is None:
        raise error_401()
    try:
        claims = decodificar_token(token)
    except TokenInvalido:
        raise error_401("Token inválido o expirado") from None

    usuario = session.get(Usuario, claims.usuario_id)
    # Usuario borrado (soft delete) o desactivado: su token ya no sirve.
    if usuario is None or not usuario.activo:
        raise error_401("Token inválido o expirado")
    return usuario


UsuarioActualDep = Annotated[Usuario, Depends(obtener_usuario_actual)]


def requiere_admin(usuario: UsuarioActualDep) -> Usuario:
    # Se usa el rol guardado en la BD (no el del token): si a alguien le
    # quitan el rol admin, pierde el permiso de inmediato.
    if usuario.rol != Rol.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para esta operación",
        )
    return usuario


AdminDep = Annotated[Usuario, Depends(requiere_admin)]


def obtener_usuario_o_404(
    usuario_id: Annotated[int, Path(gt=0, description="ID del usuario")],
    session: SessionDep,
) -> Usuario:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


UsuarioPorIdDep = Annotated[Usuario, Depends(obtener_usuario_o_404)]
