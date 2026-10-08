from logging.config import fileConfig
import asyncio

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.database import Base
from app.core.config import settings

# Importe seus models
from app.models.route_request import RouteRequest

import geoalchemy2

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url():
    return (
        f"postgresql+asyncpg://"
        f"{settings.postgres_user}:"
        f"{settings.postgres_password}@"
        f"{settings.postgres_host}:"
        f"{settings.postgres_port}/"
        f"Criminalidade"
    )


# Não deixa o Alembic considerar tabelas existentes
# que não estão nos models como tabelas removidas.
from geoalchemy2 import alembic_helpers

def include_object(object, name, type_, reflected, compare_to):
    # Your existing rule
    if type_ == "table" and reflected:
        if name in {"ocorrencias", "ocorrencias_stg", "spatial_ref_sys"}:
            return False

    # Let GeoAlchemy2 handle spatial indexes/columns
    return alembic_helpers.include_object(object, name, type_, reflected, compare_to)

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        {
            "sqlalchemy.url": get_database_url()
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()




















































































































































