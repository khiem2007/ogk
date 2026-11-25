import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from server.app.db.base import Base
import server.app.models.entities  # noqa: F401


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

environment_database_url = os.getenv("OGK_DATABASE_URL")
if environment_database_url:
    config.set_main_option("sqlalchemy.url", environment_database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql("PRAGMA busy_timeout=5000")
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
