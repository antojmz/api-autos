"""
alembic/env.py — Configuración de Alembic para este proyecto.

Alembic es la herramienta de migraciones recomendada por la documentación de
FastAPI/SQLAlchemy. Cada cambio de esquema (crear tabla, añadir columna...) se
guarda como un archivo en alembic/versions/ y se aplica con:
    alembic upgrade head      # aplica todas las migraciones pendientes
    alembic downgrade -1      # revierte la última
    alembic revision --autogenerate -m "mensaje"   # genera una nueva a partir
                                                   # de los cambios en app/models.py
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

from alembic import context

# Importar la configuración (lee .env) y los modelos. Importar app.models
# registra las tablas en SQLModel.metadata, que Alembic compara con la base
# de datos real para autogenerar migraciones.
from app.config import settings
from app import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Modo 'offline': genera el SQL (alembic upgrade head --sql) sin conectarse."""
    context.configure(
        url=settings.database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo 'online': se conecta a PostgreSQL y aplica las migraciones."""
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
