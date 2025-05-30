# from logging.config import fileConfig
from typing import Any

import sqlalchemy as sa
from sqlalchemy import pool

from alembic import context
from marvin.core.config import get_app_settings
from marvin.db.models import SqlAlchemyBase

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SqlAlchemyBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

settings = get_app_settings()

if not settings.DB_URL:
    raise Exception("DB URL not set in config")


config.set_main_option("sqlalchemy.url", settings.DB_URL.replace("%", "%%"))

PLUGIN_PREFIX = "alembic_"


def include_object(object: Any, name: str, type_: str, reflected: bool, compare_to: Any) -> bool:
    """Return True if the object should be included in the migration."""
    # Don't include objects that are not in the model
    # or that are not in the plugin prefix
    if type_ == "table":
        # Don't drop tables that are unknown in the model... unless these are really tables dropped from the plugin.
        return name in target_metadata.tables or name.startswith(PLUGIN_PREFIX)
    elif type_ == "column":
        # Don't include columns that are not in the model
        return name in target_metadata.tables[object.table.name].c
    elif type_ == "index":
        # Don't include indexes that are not in the model
        return name in target_metadata.tables[object.table.name].indexes
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = sa.engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            user_module_prefix="marvin.db.migration_types.",
            render_as_batch=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
