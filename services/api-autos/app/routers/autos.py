"""
routers/autos.py — CRUD de autos.

Concepto clave: un `APIRouter` agrupa rutas relacionadas. Luego `main.py` lo
registra con `app.include_router(...)`. Es la forma de dividir una API grande
en varios archivos.

Decoradores de ruta: `@router.get(...)`, `@router.post(...)`, etc. asocian una
función Python a un método HTTP + ruta. Parámetros útiles:
  - `status_code`: código HTTP de éxito (201 al crear, 204 al borrar...).
  - `response_model`: modelo Pydantic con el que se FILTRA y valida la
    respuesta. Aunque la función devuelva un objeto con más campos, solo se
    envían los declarados (evita filtrar datos internos).
"""

from typing import Annotated

from auth_jwt import Rol, obtener_claims, requiere_rol
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import col, func, select

from app.dependencies import AutoDep, PaginacionDep, SessionDep
from app.models import Auto, Modelo
from app.schemas import AutoCreate, AutoPublic, AutoUpdate, Pagina

# prefix: todas las rutas de este router empiezan con /autos.
# tags: agrupa los endpoints bajo "Autos" en la documentación /docs.
# dependencies: se ejecutan ANTES de cada endpoint del router. Con
# `obtener_claims` (librería compartida libs/auth-jwt) TODAS las rutas exigen
# un token JWT válido emitido por api-usuarios; si falta o no es válido -> 401.
# `responses` documenta esos errores en /docs.
router = APIRouter(
    prefix="/autos",
    tags=["Autos"],
    dependencies=[Depends(obtener_claims)],
    responses={401: {"description": "Falta el token o no es válido"}},
)


def _escapar_like(texto: str) -> str:
    """
    En LIKE/ILIKE, '%' y '_' son comodines. Los escapamos para que el texto
    del usuario se busque literalmente (sino, buscar "%" devolvería todo).
    """
    return texto.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


@router.post(
    "",
    response_model=AutoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un auto",
)
def crear_auto(datos: AutoCreate, session: SessionDep) -> Auto:
    # `datos` ya llega validado: si el JSON fuera inválido, FastAPI habría
    # respondido 422 sin entrar a esta función.
    # Creamos el objeto ORM campo a campo desde el esquema validado: el
    # cliente no puede fijar el `id` ni ningún otro campo interno.
    auto = Auto(marca=datos.marca, fecha_ingreso=datos.fecha_ingreso)
    session.add(auto)
    session.commit()  # INSERT ... confirmado en PostgreSQL
    session.refresh(auto)  # recarga el objeto para obtener el id generado
    return auto


@router.get("", response_model=Pagina[AutoPublic], summary="Listar autos (paginado)")
def listar_autos(
    session: SessionDep,
    paginacion: PaginacionDep,
    marca: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=50,
            description="Filtra por marca (contiene, sin distinguir mayúsculas)",
        ),
    ] = None,
) -> Pagina[AutoPublic]:
    consulta = select(Auto)
    if marca:
        # OWASP — Inyección SQL: el ORM envía `marca` como PARÁMETRO de la
        # consulta (nunca concatenado al SQL), por lo que un valor como
        # "' OR 1=1 --" se busca como texto literal y no altera la consulta.
        patron = f"%{_escapar_like(marca.strip())}%"
        consulta = consulta.where(col(Auto.marca).ilike(patron, escape="\\"))

    # Total de registros que cumplen el filtro (para que el cliente sepa
    # cuántas páginas hay).
    total = session.exec(select(func.count()).select_from(consulta.subquery())).one()

    autos = session.exec(
        consulta.order_by(col(Auto.id)).offset(paginacion.skip).limit(paginacion.limit)
    ).all()

    return Pagina[AutoPublic](
        total=total,
        skip=paginacion.skip,
        limit=paginacion.limit,
        items=[AutoPublic.model_validate(auto) for auto in autos],
    )


@router.get("/{auto_id}", response_model=AutoPublic, summary="Obtener un auto por ID")
def obtener_auto(auto: AutoDep) -> Auto:
    # Toda la lógica (validar el ID, buscar en BD, 404 si no existe) está en
    # la dependencia `obtener_auto_o_404`. El endpoint queda en una línea.
    return auto


@router.put("/{auto_id}", response_model=AutoPublic, summary="Actualizar un auto")
def actualizar_auto(datos: AutoUpdate, auto: AutoDep, session: SessionDep) -> Auto:
    # Regla de negocio: un modelo no puede haber ingresado antes que su auto.
    # Si la nueva fecha del auto es posterior a la de algún modelo, la
    # actualización dejaría datos inconsistentes -> 409 Conflict.
    fecha_modelo_mas_antiguo = session.exec(
        select(func.min(Modelo.fecha_ingreso)).where(Modelo.auto_id == auto.id)
    ).one()
    if fecha_modelo_mas_antiguo and datos.fecha_ingreso > fecha_modelo_mas_antiguo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La fecha de ingreso del auto no puede ser posterior a la de sus modelos",
        )

    auto.marca = datos.marca
    auto.fecha_ingreso = datos.fecha_ingreso
    session.add(auto)
    session.commit()
    session.refresh(auto)
    return auto


@router.delete(
    "/{auto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un auto (y sus modelos) — solo admin",
    # Además del token (exigido por el router), esta ruta requiere rol admin:
    # un usuario autenticado sin ese rol recibe 403 Forbidden.
    dependencies=[Depends(requiere_rol(Rol.ADMIN))],
    responses={403: {"description": "Requiere rol admin"}},
)
def eliminar_auto(auto: AutoDep, session: SessionDep) -> None:
    # Gracias a `cascade_delete=True` (ORM) y `ON DELETE CASCADE` (BD), los
    # modelos asociados también se eliminan.
    session.delete(auto)
    session.commit()
    # 204 No Content: éxito sin cuerpo de respuesta.
