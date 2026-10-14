"""Alembic runs migrations through the same async engine settings as the app."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  (registers all tables)
from app.config import get_settings
from app.db import Base

config = context.config
if config.config_file_name and not config.attributes.get("skip_logging"):
    fileConfig(config.config_file_name)

# Tests pass their own URL via config.attributes["url"].
URL = config.attributes.get("url") or get_settings().database_url


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


asyncio.run(run_async_migrations())
