"""
dependencies.py — Inyección de dependencias (`Depends`).

Concepto clave: una "dependencia" es una función que FastAPI ejecuta ANTES del
endpoint. Su resultado se inyecta como parámetro. Sirve para reutilizar lógica
común (abrir la sesión de BD, leer parámetros de paginación, buscar un recurso
o devolver 404...) sin repetirla en cada ruta.

Las dependencias pueden depender de otras: `obtener_auto_o_404` usa
`SessionDep`, y FastAPI resuelve el árbol completo automáticamente.

`Annotated[Tipo, Depends(func)]` crea un alias reutilizable: en el endpoint
basta con escribir `session: SessionDep`.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query, status
from sqlmodel import Session

from app.database import get_session
from app.models import Auto, Modelo

LIMITE_MAXIMO_PAGINA = 100

# Sesión de base de datos por petición.
SessionDep = Annotated[Session, Depends(get_session)]


@dataclass(frozen=True)
class Paginacion:
    skip: int
    limit: int


def parametros_paginacion(
    # Query(...) declara un parámetro de la URL (?skip=0&limit=10) con reglas.
    # ge = "greater or equal", le = "less or equal".
    skip: Annotated[int, Query(ge=0, description="Registros a saltar")] = 0,
    # Limitar el tamaño de página evita respuestas enormes que saturen el
    # servidor (OWASP API4: consumo de recursos sin restricción).
    limit: Annotated[
        int, Query(ge=1, le=LIMITE_MAXIMO_PAGINA, description="Máximo de registros")
    ] = 10,
) -> Paginacion:
    return Paginacion(skip=skip, limit=limit)


PaginacionDep = Annotated[Paginacion, Depends(parametros_paginacion)]


def obtener_auto_o_404(
    # Path(...) valida el parámetro de ruta {auto_id}: debe ser entero > 0.
    # Si llega "abc" o "-1", FastAPI responde 422 automáticamente.
    auto_id: Annotated[int, Path(gt=0, description="ID del auto")],
    session: SessionDep,
) -> Auto:
    auto = session.get(Auto, auto_id)
    if auto is None:
        # HTTPException corta la petición y responde con ese código y mensaje.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auto no encontrado")
    return auto


AutoDep = Annotated[Auto, Depends(obtener_auto_o_404)]


def obtener_modelo_o_404(
    modelo_id: Annotated[int, Path(gt=0, description="ID del modelo")],
    session: SessionDep,
) -> Modelo:
    modelo = session.get(Modelo, modelo_id)
    if modelo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")
    return modelo


ModeloDep = Annotated[Modelo, Depends(obtener_modelo_o_404)]
