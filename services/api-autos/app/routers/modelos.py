"""
routers/modelos.py — Modelos de cada auto.

Este router no usa `prefix` porque las rutas pedidas tienen formas distintas:
  - POST /modelo         -> crear un modelo para un auto existente
  - GET  /modelos/autos  -> listar autos con sus modelos anidados
"""

from auth_jwt import obtener_claims
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import col, func, select

from app.dependencies import PaginacionDep, SessionDep
from app.models import Auto, Modelo
from app.schemas import AutoConModelos, ModeloCreate, ModeloPublic, Pagina

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
