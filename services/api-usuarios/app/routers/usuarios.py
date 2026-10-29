"""
routers/usuarios.py — CRUD de usuarios (rutas protegidas).

Permisos:
  /usuarios/me...         cualquier usuario autenticado (sobre sí mismo)
  GET /usuarios/{id}      admin, o el propio usuario
  resto de /usuarios      solo admin

401 = no autenticado (falta token o no es válido).
403 = autenticado, pero sin permiso.

IMPORTANTE: las rutas "/me" se declaran ANTES que "/{usuario_id}". FastAPI
evalúa las rutas en orden; si "/{usuario_id}" fuera primero, "/me" se
intentaría interpretar como un id.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Session, col, func, or_, select

from auth_jwt import Rol
from app.dependencies import AdminDep, PaginacionDep, SessionDep, UsuarioActualDep, UsuarioPorIdDep
from app.models import Usuario, ahora_utc
from app.schemas import (
    CambioPassword,
    Pagina,
    UsuarioCreateAdmin,
    UsuarioPublic,
    UsuarioUpdateAdmin,
    UsuarioUpdateMe,
)
from app.seguridad import hashear_password, verificar_password
from app.servicios import crear_usuario, marcar_actualizado, verificar_unicidad

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    responses={401: {"description": "Falta el token o no es válido"}},
)


def _escapar_like(texto: str) -> str:
    """Escapa los comodines de LIKE (% y _) para buscar el texto literal."""
    return texto.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _aplicar_cambios(session: Session, usuario: Usuario, datos: UsuarioUpdateMe) -> None:
    """
    Aplica solo los campos que el cliente envió (PATCH = actualización parcial).
    `exclude_unset=True` distingue "no enviado" de "enviado".
    """
    cambios = datos.model_dump(exclude_unset=True)
    verificar_unicidad(
        session,
        username=cambios.get("username"),
        email=cambios.get("email"),
        excluir_id=usuario.id,
    )
    # La contraseña nunca se copia tal cual: se transforma en hash.
    if "password" in cambios:
        usuario.password_hash = hashear_password(cambios.pop("password"))
    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)
    marcar_actualizado(usuario)
    session.add(usuario)
    session.commit()
    session.refresh(usuario)


# ---------------------------------------------------------------------------
# Perfil propio (/me)
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UsuarioPublic, summary="Mi perfil")
def mi_perfil(usuario: UsuarioActualDep) -> Usuario:
    return usuario


@router.patch(
    "/me",
    response_model=UsuarioPublic,
    summary="Actualizar mi perfil (parcial)",
    responses={409: {"description": "El username o el email ya están registrados"}},
)
def actualizar_mi_perfil(datos: UsuarioUpdateMe, usuario: UsuarioActualDep, session: SessionDep) -> Usuario:
    # `UsuarioUpdateMe` no tiene `rol` ni `activo`: un usuario no puede
    # darse permisos a sí mismo (y extra="forbid" rechaza esos campos).
    _aplicar_cambios(session, usuario, datos)
    return usuario


@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar mi contraseña",
    responses={400: {"description": "La contraseña actual no es correcta"}},
)
def cambiar_mi_password(datos: CambioPassword, usuario: UsuarioActualDep, session: SessionDep) -> None:
    # Pedir la contraseña actual evita que alguien con un token robado (o
    # con la sesión abierta en otro equipo) cambie la contraseña.
    if not verificar_password(datos.password_actual, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta",
        )
    usuario.password_hash = hashear_password(datos.password_nueva)
    marcar_actualizado(usuario)
    session.add(usuario)
    session.commit()


# ---------------------------------------------------------------------------
# Administración de usuarios
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=UsuarioPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un usuario — solo admin",
    responses={403: {"description": "Requiere rol admin"}, 409: {"description": "Duplicado"}},
)
def crear_usuario_admin(datos: UsuarioCreateAdmin, _admin: AdminDep, session: SessionDep) -> Usuario:
    return crear_usuario(
        session,
        username=datos.username,
        email=datos.email,
        nombre_completo=datos.nombre_completo,
        password=datos.password,
        rol=datos.rol,
    )


@router.get(
    "",
    response_model=Pagina[UsuarioPublic],
    summary="Listar usuarios (paginado y con filtros) — solo admin",
    responses={403: {"description": "Requiere rol admin"}},
)
def listar_usuarios(
    _admin: AdminDep,
    session: SessionDep,
    paginacion: PaginacionDep,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=50, description="Busca en username o email (contiene)"),
    ] = None,
    rol: Annotated[Rol | None, Query(description="Filtra por rol")] = None,
    activo: Annotated[bool | None, Query(description="true = activos, false = desactivados/eliminados")] = None,
) -> Pagina[UsuarioPublic]:
    consulta = select(Usuario)
    if q:
        patron = f"%{_escapar_like(q.strip().lower())}%"
        consulta = consulta.where(
            or_(
                col(Usuario.username).like(patron, escape="\\"),
                col(Usuario.email).like(patron, escape="\\"),
            )
        )
    if rol is not None:
        consulta = consulta.where(Usuario.rol == rol)
    if activo is not None:
        consulta = consulta.where(Usuario.activo == activo)

    total = session.exec(select(func.count()).select_from(consulta.subquery())).one()
    usuarios = session.exec(
        consulta.order_by(col(Usuario.id)).offset(paginacion.skip).limit(paginacion.limit)
    ).all()
    return Pagina[UsuarioPublic](
        total=total,
        skip=paginacion.skip,
        limit=paginacion.limit,
        items=[UsuarioPublic.model_validate(u) for u in usuarios],
    )


@router.get(
    "/{usuario_id}",
    response_model=UsuarioPublic,
    summary="Obtener un usuario por ID — admin o el propio usuario",
    responses={403: {"description": "Sin permiso"}, 404: {"description": "No existe"}},
)
def obtener_usuario(objetivo: UsuarioPorIdDep, actual: UsuarioActualDep) -> Usuario:
    # Control de acceso a nivel de objeto (OWASP API1 - BOLA): no basta con
    # estar autenticado; hay que comprobar que el recurso es tuyo o eres admin.
    if actual.rol != Rol.ADMIN and actual.id != objetivo.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta operación")
    return objetivo


@router.patch(
    "/{usuario_id}",
    response_model=UsuarioPublic,
    summary="Actualizar un usuario (parcial) — solo admin",
    responses={
        400: {"description": "Un admin no puede quitarse su rol ni desactivarse"},
        403: {"description": "Requiere rol admin"},
        404: {"description": "No existe o está eliminado"},
        409: {"description": "Duplicado"},
    },
)
def actualizar_usuario(
    datos: UsuarioUpdateAdmin, objetivo: UsuarioPorIdDep, admin: AdminDep, session: SessionDep
) -> Usuario:
    if objetivo.eliminado_en is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    # Evita que el sistema se quede sin administradores por accidente.
    if objetivo.id == admin.id and (
        (datos.rol is not None and datos.rol != Rol.ADMIN) or datos.activo is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes quitarte el rol de admin ni desactivar tu propia cuenta",
        )
    _aplicar_cambios(session, objetivo, datos)
    return objetivo


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un usuario (soft delete) — solo admin",
    responses={
        400: {"description": "Un admin no puede eliminarse a sí mismo"},
        403: {"description": "Requiere rol admin"},
        404: {"description": "No existe o ya está eliminado"},
    },
)
def eliminar_usuario(objetivo: UsuarioPorIdDep, admin: AdminDep, session: SessionDep) -> None:
    if objetivo.eliminado_en is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if objetivo.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes eliminar tu propia cuenta")

    # SOFT DELETE: la fila se conserva (historial, auditoría) pero el usuario
    # queda desactivado: no puede iniciar sesión y sus tokens dejan de servir
    # en este servicio. Su username y email siguen reservados.
    objetivo.activo = False
    objetivo.eliminado_en = ahora_utc()
    marcar_actualizado(objetivo)
    session.add(objetivo)
    session.commit()
