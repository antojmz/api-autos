"""
database.py — Conexión a PostgreSQL.

- El *engine* es el objeto que administra el pool de conexiones. Se crea UNA
  sola vez para toda la aplicación.
- Una *Session* es una "unidad de trabajo": agrupa las operaciones de una
  petición y las confirma (commit) o descarta (rollback) juntas.

IMPORTANTE: aquí NO llamamos a `SQLModel.metadata.create_all()`. Las tablas se
crean y modifican exclusivamente con migraciones de Alembic (`alembic upgrade
head`). Así cada cambio de esquema queda versionado, es reproducible en otros
entornos y se puede revertir.
"""

from collections.abc import Iterator

from sqlmodel import Session, create_engine

from app.config import settings

# pool_pre_ping=True: antes de usar una conexión del pool comprueba que siga
# viva (evita errores si PostgreSQL se reinició).
# echo=False: no imprime el SQL en consola (ponlo en True para aprender qué
# consultas genera el ORM).
engine = create_engine(settings.database_url, pool_pre_ping=True, echo=False)


def get_session() -> Iterator[Session]:
    """
    Dependencia de FastAPI con `yield`.

    FastAPI ejecuta el código ANTES del `yield` al inicio de la petición,
    entrega la sesión al endpoint y, cuando la respuesta termina, ejecuta lo
    que hay DESPUÉS (aquí, el cierre del bloque `with`, que cierra la sesión y
    hace rollback de cualquier cambio no confirmado).
    """
    with Session(engine) as session:
        yield session
