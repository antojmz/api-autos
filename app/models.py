"""
models.py — Tablas de la base de datos (capa de persistencia).

Usamos SQLModel, la librería del mismo autor de FastAPI que combina SQLAlchemy
(ORM) y Pydantic. Una clase con `table=True` representa una tabla real.

Estas clases describen CÓMO se guardan los datos. Las reglas de validación de
lo que envía el cliente viven en `schemas.py`: separar ambas cosas evita que un
cliente pueda escribir campos internos (como `id`) — "mass assignment".

Alembic lee `SQLModel.metadata` (que se llena al importar este módulo) para
autogenerar las migraciones.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel


class Auto(SQLModel, table=True):
    __tablename__ = "autos"

    # `default=None` + `primary_key=True`: el id lo genera PostgreSQL
    # (columna SERIAL / IDENTITY autoincremental).
    id: int | None = Field(default=None, primary_key=True)
    # max_length=50 -> VARCHAR(50). index=True crea un índice para acelerar
    # los filtros por marca.
    marca: str = Field(max_length=50, index=True)
    fecha_ingreso: date

    # Relación 1 a N: un auto tiene muchos modelos.
    # cascade_delete=True: al borrar un Auto con el ORM se borran sus modelos.
    # order_by: los modelos se devuelven siempre ordenados por id.
    modelos: list["Modelo"] = Relationship(
        back_populates="auto",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "Modelo.id"},
    )


class Modelo(SQLModel, table=True):
    __tablename__ = "modelos"

    # Restricciones a nivel de base de datos: "defensa en profundidad".
    # Aunque Pydantic ya valida, si alguien inserta datos por otra vía
    # (otro servicio, SQL manual) PostgreSQL también los rechaza.
    __table_args__ = (
        CheckConstraint("precio > 0", name="ck_modelos_precio_positivo"),
        CheckConstraint("anio >= 1886", name="ck_modelos_anio_minimo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    # Clave foránea hacia autos.id. ondelete="CASCADE" hace que la propia
    # base de datos borre los modelos si se borra el auto.
    auto_id: int = Field(foreign_key="autos.id", ondelete="CASCADE", index=True)
    nombre: str = Field(max_length=60)
    anio: int
    # NUMERIC(12, 2): los precios NUNCA se guardan como float (errores de
    # redondeo); Decimal es exacto.
    precio: Decimal = Field(max_digits=12, decimal_places=2)
    fecha_ingreso: date

    auto: Auto | None = Relationship(back_populates="modelos")
