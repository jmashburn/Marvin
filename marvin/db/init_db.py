import os
from collections.abc import Callable
from pathlib import Path
from time import sleep

from sqlalchemy import engine, orm, text

from alembic import command, config, script
from alembic.config import Config
from alembic.runtime import migration
from marvin.core import root_logger
from marvin.core.config import get_app_plugins, get_app_settings
from marvin.db.db_setup import session_context
from marvin.repos.seed.init_users import default_user_init

from marvin.db.fixes.fix_migration_data import fix_migration_data
from marvin.repos.all_repositories import get_repositories
from marvin.repos.repository_factory import AllRepositories

from marvin.schemas.group.group import GroupCreate, GroupRead
from marvin.services.group.group_service import GroupService

PROJECT_DIR = Path(__file__).parent.parent.parent

logger = root_logger.get_logger()


def init_db(session: orm.Session) -> None:
    settings = get_app_settings()

    instance_repos = get_repositories(session)

    default_group = default_group_init(instance_repos, settings.DEFAULT_GROUP)
    group_repos = get_repositories(session, group_id=default_group.id)
    default_user_init(group_repos)


def default_group_init(repos: AllRepositories, name: str) -> GroupRead:
    logger.info("Generating Default Group")
    return GroupService.create_group(repos, GroupCreate(name=name))


def safe_try(func: Callable):
    try:
        func()
    except Exception as e:
        logger.error(f"Error calling '{func.__name__}': {e}")


def connect(session: orm.Session) -> bool:
    try:
        session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return False


def include_name(name, type_, parent_names):
    if type_ == "table":
        # Don't drop tables that are unknown in the model... unless these are really tables dropped from the plugin.
        return name in target_metadata.tables or name.startswith(PLUGIN_PREFIX)
    return True


def db_is_at_head(alembic_cfg: config.Config) -> bool:
    settings = get_app_settings()
    url = settings.DB_URL
    if not url:
        raise ValueError("No database url found")

    connectable = engine.create_engine(url)
    directory = script.ScriptDirectory.from_config(alembic_cfg)
    with connectable.connect() as connection:
        context = migration.MigrationContext.configure(
            connection=connection,
            opts={
                "version_table": alembic_cfg.get_main_option("version_table") or "alembic_version",
                "include_name": include_name,
            },
        )
        return set(context.get_current_heads()) == set(directory.get_heads())


def main():
    max_retry = 10
    wait_second = 1

    settings = get_app_settings()

    with session_context() as session:
        while True:
            if connect(session):
                logger.info("Database connection established.")
                break

            logger.error("Database connection failed - exiting application.")
            max_retry -= 1

            sleep(wait_second)

            if max_retry == 0:
                raise ConnectionError("Database connection failed - exiting application.")

        alembic_cfg_paths = {"main": os.getenv("ALEMBIC_CONFIG_FILE", default=str(PROJECT_DIR / "alembic.ini"))}

        if settings.PLUGINS:
            logger.info("-------Plugins Alembic Enabled-------")
            plugins = get_app_plugins(settings.PLUGIN_PREFIX)
            for plugin_name, plugin in plugins.LOADED_PLUGINS.items():
                PLUGIN_DIR = Path(os.path.dirname(plugin.__file__))
                plugin_alembic_path = str(PLUGIN_DIR / "alembic.ini")

                if os.path.isfile(plugin_alembic_path):
                    plugin_name = plugin.__meta__["name"]
                    logger.debug(f"-------Adding Plugin Alembic: {plugin_name}-------")
                    alembic_cfg_paths.update({f"{plugin.__meta__['name']}": plugin_alembic_path})

        for name, alembic_cfg_path in alembic_cfg_paths.items():
            if not os.path.isfile(alembic_cfg_path):
                raise Exception("Provided alembic config path doesn't exist")

            alembic_cfg = Config(alembic_cfg_path)
            if name != "main" and os.path.isdir(str(PLUGIN_DIR / "alembic")):
                VERSION_TABLE = f"{name}_alembic_version"
                alembic_cfg.set_main_option("script_location", str(PLUGIN_DIR / "alembic"))
                alembic_cfg.set_main_option("version_table", VERSION_TABLE)
                alembic_cfg.set_main_option("include_name", "include_name")

            if db_is_at_head(alembic_cfg):
                logger.debug(f"Migration not needed for {name}.")
            else:
                logger.debug(f"Migration needed. Performing migration for {name}...")
                command.upgrade(alembic_cfg, "head")

            if session.get_bind().name == "postgresql":
                session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

        db = get_repositories(session, group_id=None)

        safe_try(lambda: fix_migration_data(session))
        if db.users.get_all():
            logger.debug("Databse exists")
        else:
            logger.info("Database contains no users initializing...")
            init_db(session)
