"""
routers/auth.py — Registro e inicio de sesión (públicos).

Flujo de autenticación:
  1. POST /auth/registro  -> crea la cuenta (rol "usuario").
  2. POST /auth/login     -> verifica usuario+contraseña y devuelve un JWT.
  3. El cliente envía el token en cada petición protegida, en cualquier
     servicio del monorepo:   Authorization: Bearer <token>
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import or_, select

from auth_jwt import Rol, crear_token_acceso, error_401
from app.dependencies import SessionDep
from app.models import Usuario
from app.schemas import PASSWORD_MAX, RegistroUsuario, Token, UsuarioPublic
from app.seguridad import simular_verificacion, verificar_password
from app.servicios import crear_usuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/registro",
    response_model=UsuarioPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una cuenta nueva",
    responses={409: {"description": "El username o el email ya están registrados"}},
)
def registrar(datos: RegistroUsuario, session: SessionDep) -> Usuario:
    # El rol se fija aquí, en el servidor. `RegistroUsuario` no tiene campo
    # `rol` y prohíbe campos extra: nadie puede registrarse como admin.
    return crear_usuario(
        session,
        username=datos.username,
        email=datos.email,
        nombre_completo=datos.nombre_completo,
        password=datos.password,
        rol=Rol.USUARIO,
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión y obtener un token JWT",
    responses={401: {"description": "Credenciales incorrectas"}},
)
def login(
    # OAuth2PasswordRequestForm: el estándar OAuth2 exige que el login se
    # envíe como FORMULARIO (application/x-www-form-urlencoded) con los campos
    # `username` y `password`, no como JSON. Así funciona el botón
    # "Authorize" de /docs. Aquí `username` admite también el email.
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> Token:
    identificador = formulario.username.strip().lower()
    password = formulario.password

    # Entradas absurdamente largas: se rechazan sin gastar CPU en el hash.
    if len(identificador) > 254 or len(password) > PASSWORD_MAX:
        raise error_401("Credenciales incorrectas")

    usuario = session.exec(
        select(Usuario).where(or_(Usuario.username == identificador, Usuario.email == identificador))
    ).first()

    if usuario is None:
        # El usuario no existe: aun así "verificamos" contra un hash ficticio
        # para tardar lo mismo (evita descubrir usuarios por tiempo).
        simular_verificacion(password)
        raise error_401("Credenciales incorrectas")

    # Mismo mensaje para "contraseña incorrecta" y "cuenta desactivada": no
    # damos pistas a un atacante sobre qué parte falló.
    if not verificar_password(password, usuario.password_hash) or not usuario.activo:
        raise error_401("Credenciales incorrectas")

    token, expira_en = crear_token_acceso(usuario.id, usuario.username, Rol(usuario.rol))
    return Token(access_token=token, expires_in=expira_en)
