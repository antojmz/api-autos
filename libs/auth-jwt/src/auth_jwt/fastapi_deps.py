"""
fastapi_deps.py — Dependencias de FastAPI para proteger rutas ("guards").

Uso en un servicio:

    from auth_jwt import ClaimsDep, obtener_claims, requiere_rol, Rol

    # Proteger TODAS las rutas de un router:
    router = APIRouter(dependencies=[Depends(obtener_claims)])

    # Leer los datos del usuario en un endpoint:
    def mi_ruta(claims: ClaimsDep): ...

    # Exigir un rol:
    @router.delete("/{id}", dependencies=[Depends(requiere_rol(Rol.ADMIN))])

Estas dependencias son "stateless": solo validan el token, sin consultar la
base de datos. Un usuario desactivado conserva acceso hasta que su token
expira (por eso los tokens duran poco).
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_jwt.tokens import ClaimsToken, Rol, TokenInvalido, decodificar_token

# HTTPBearer lee la cabecera "Authorization: Bearer <token>" y además añade el
# botón "Authorize" en /docs. auto_error=False: si falta la cabecera no lanza
# su propio error (403), sino que devolvemos nosotros el 401 correcto.
esquema_bearer = HTTPBearer(auto_error=False, description="Token JWT obtenido en api-usuarios /auth/login")


def error_401(detalle: str = "No autenticado") -> HTTPException:
    """
    401 Unauthorized = "no sé quién eres" (falta token o no es válido).
    La cabecera WWW-Authenticate indica al cliente qué esquema usar (RFC 6750).
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def obtener_claims(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)],
) -> ClaimsToken:
    if credenciales is None:
        raise error_401()
    try:
        return decodificar_token(credenciales.credentials)
    except TokenInvalido:
        # Mensaje genérico: no revelamos si caducó, si la firma falla, etc.
        raise error_401("Token inválido o expirado") from None


ClaimsDep = Annotated[ClaimsToken, Depends(obtener_claims)]


def requiere_rol(*roles: Rol) -> Callable[[ClaimsToken], ClaimsToken]:
    """
    Fábrica de dependencias: devuelve una dependencia que exige uno de los roles.
    403 Forbidden = "sé quién eres, pero no tienes permiso".
    """

    def _verificar(claims: ClaimsDep) -> ClaimsToken:
        if claims.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta operación",
            )
        return claims

    return _verificar
