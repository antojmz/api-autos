"""
servicios.py — Lógica de negocio reutilizada por varios routers.

Mantener esta lógica fuera de los endpoints evita repetirla (registro público,
alta por admin y creación del admin inicial crean usuarios de la misma forma).
"""

from fastapi import HTTPException, status
from sqlmodel import Session, or_, select

from auth_jwt import Rol
from app.models import Usuario, ahora_utc
from app.seguridad import hashear_password


def verificar_unicidad(
    session: Session, *, username: str | None, email: str | None, excluir_id: int | None = None
) -> None:
    """
    409 Conflict si el username o el email ya los usa OTRO usuario (incluidos
    los borrados con soft delete: siguen reservados).
    El mensaje no dice cuál de los dos está repetido ni a quién pertenece.
    """
    condiciones = []
    if username is not None:
        condiciones.append(Usuario.username == username)
    if email is not None:
        condiciones.append(Usuario.email == email)
    if not condiciones:
        return

    consulta = select(Usuario.id).where(or_(*condiciones))
    if excluir_id is not None:
        consulta = consulta.where(Usuario.id != excluir_id)
    if session.exec(consulta).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El username o el email ya están registrados",
        )


def crear_usuario(
    session: Session, *, username: str, email: str, nombre_completo: str, password: str, rol: Rol
) -> Usuario:
    """Valida unicidad, hashea la contraseña y guarda el usuario."""
    verificar_unicidad(session, username=username, email=email)
    usuario = Usuario(
        username=username,
        email=email,
        nombre_completo=nombre_completo,
        # La contraseña se transforma en hash ANTES de tocar la base de datos.
        password_hash=hashear_password(password),
        rol=rol,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def marcar_actualizado(usuario: Usuario) -> None:
    usuario.actualizado_en = ahora_utc()
