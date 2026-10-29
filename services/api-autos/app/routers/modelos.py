"""
routers/modelos.py — Modelos de cada auto.

Este router no usa `prefix` porque las rutas tienen formas distintas:
  - POST   /modelo          -> crear un modelo para un auto existente
  - GET    /modelos         -> listar modelos (paginado, filtro por auto)
  - GET    /modelos/autos   -> listar autos con sus modelos anidados
  - GET    /modelos/{id}    -> obtener un modelo
  - PUT    /modelos/{id}    -> reemplazar un modelo
  - DELETE /modelos/{id}    -> eliminar un modelo (solo admin)

IMPORTANTE: "/modelos/autos" se declara ANTES que "/modelos/{modelo_id}".
FastAPI prueba las rutas en orden; si "/modelos/{modelo_id}" fuera primero,
"autos" se intentaría convertir a entero y la petición fallaría con 422.
"""

from typing import Annotated

from auth_jwt import Rol, obtener_claims, requiere_rol
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import col, func, select

from app.dependencies import ModeloDep, PaginacionDep, SessionDep
from app.models import Auto, Modelo
from app.schemas import AutoConModelos, ModeloCreate, ModeloPublic, ModeloUpdate, Pagina

# Todas las rutas exigen un token JWT válido (ver routers/autos.py).
router = APIRouter(
    tags=["Modelos"],
    dependencies=[Depends(obtener_claims)],
    responses={401: {"description": "Falta el token o no es válido"}},
)


@router.post(
    "/modelo",
    response_model=ModeloPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un modelo de auto",
    # `responses` documenta en /docs otros códigos posibles además del 201.
    responses={404: {"description": "El auto indicado no existe"}},
)
def crear_modelo(datos: ModeloCreate, session: SessionDep) -> Modelo:
    # Validación de integridad referencial con un mensaje claro: verificamos
    # que el auto exista antes de insertar (si no, PostgreSQL lanzaría un
    # error de clave foránea menos amigable).
    auto = session.get(Auto, datos.auto_id)
    if auto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auto no encontrado")

    # Regla de negocio que involucra dos entidades: Pydantic no puede
    # validarla sola porque necesita consultar la BD.
    if datos.fecha_ingreso < auto.fecha_ingreso:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha de ingreso del modelo no puede ser anterior a la del auto",
        )

    modelo = Modelo(
        auto_id=datos.auto_id,
        nombre=datos.nombre,
        anio=datos.anio,
        precio=datos.precio,
        fecha_ingreso=datos.fecha_ingreso,
    )
    session.add(modelo)
    session.commit()
    session.refresh(modelo)
    return modelo


@router.get(
    "/modelos/autos",
    response_model=Pagina[AutoConModelos],
    summary="Listar autos con sus modelos (paginado)",
)
def listar_autos_con_modelos(
    session: SessionDep, paginacion: PaginacionDep
) -> Pagina[AutoConModelos]:
    total = session.exec(select(func.count()).select_from(Auto)).one()

    # selectinload: carga los modelos de TODOS los autos de la página en una
    # sola consulta extra (SELECT ... WHERE auto_id IN (...)). Sin esto, se
    # haría una consulta por cada auto: el clásico problema "N+1".
    autos = session.exec(
        select(Auto)
        .options(selectinload(Auto.modelos))  # type: ignore[arg-type]
        .order_by(col(Auto.id))
        .offset(paginacion.skip)
        .limit(paginacion.limit)
    ).all()

    return Pagina[AutoConModelos](
        total=total,
        skip=paginacion.skip,
        limit=paginacion.limit,
        items=[AutoConModelos.model_validate(auto) for auto in autos],
    )


@router.get(
    "/modelos",
    response_model=Pagina[ModeloPublic],
    summary="Listar modelos (paginado, filtro opcional por auto)",
)
def listar_modelos(
    session: SessionDep,
    paginacion: PaginacionDep,
    auto_id: Annotated[int | None, Query(gt=0, description="Solo los modelos de este auto")] = None,
) -> Pagina[ModeloPublic]:
    consulta = select(Modelo)
    if auto_id is not None:
        consulta = consulta.where(Modelo.auto_id == auto_id)

    total = session.exec(select(func.count()).select_from(consulta.subquery())).one()
    modelos = session.exec(
        consulta.order_by(col(Modelo.id)).offset(paginacion.skip).limit(paginacion.limit)
    ).all()
    return Pagina[ModeloPublic](
        total=total,
        skip=paginacion.skip,
        limit=paginacion.limit,
        items=[ModeloPublic.model_validate(m) for m in modelos],
    )


@router.get(
    "/modelos/{modelo_id}",
    response_model=ModeloPublic,
    summary="Obtener un modelo por ID",
    responses={404: {"description": "No existe"}},
)
def obtener_modelo(modelo: ModeloDep) -> Modelo:
    # Igual que en autos: la dependencia valida el ID y devuelve 404 si no existe.
    return modelo


@router.put(
    "/modelos/{modelo_id}",
    response_model=ModeloPublic,
    summary="Actualizar un modelo (reemplazo completo)",
    responses={404: {"description": "No existe"}},
)
def actualizar_modelo(datos: ModeloUpdate, modelo: ModeloDep, session: SessionDep) -> Modelo:
    # Misma regla de negocio que al crear: el modelo no puede haber ingresado
    # antes que su auto.
    auto = session.get(Auto, modelo.auto_id)
    if auto is not None and datos.fecha_ingreso < auto.fecha_ingreso:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha de ingreso del modelo no puede ser anterior a la del auto",
        )

    # Campo a campo desde el esquema validado (nunca setattr con datos sin filtrar).
    modelo.nombre = datos.nombre
    modelo.anio = datos.anio
    modelo.precio = datos.precio
    modelo.fecha_ingreso = datos.fecha_ingreso
    session.add(modelo)
    session.commit()
    session.refresh(modelo)
    return modelo


@router.delete(
    "/modelos/{modelo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un modelo — solo admin",
    # Igual que eliminar un auto: además del token, exige rol admin (403 si no).
    dependencies=[Depends(requiere_rol(Rol.ADMIN))],
    responses={403: {"description": "Requiere rol admin"}, 404: {"description": "No existe"}},
)
def eliminar_modelo(modelo: ModeloDep, session: SessionDep) -> None:
    session.delete(modelo)
    session.commit()
