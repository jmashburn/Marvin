"""
This module handles the initialization and migration of the Marvin database.

It includes functions to:
- Connect to the database.
- Run Alembic migrations for the main application and any installed plugins.
- Initialize default data (e.g., default group and user).
- Initialize plugin-specific database schemas.
- Apply any necessary data fixes after migrations.
"""
import os
from collections.abc import Callable
from pathlib import Path
from time import sleep

from sqlalchemy import engine, orm, text

from alembic import command, config, script
from alembic.config import Config
from alembic.runtime import migration
from marvin.core import root_logger
from marvin.core.config import AppPlugins, get_app_plugins, get_app_settings
from marvin.db.db_setup import session_context
from marvin.db.fixes.fix_migration_data import fix_migration_data
from marvin.repos.all_repositories import get_repositories
from marvin.repos.repository_factory import AllRepositories
from marvin.repos.seed.init_users import default_user_init
from marvin.services.seeders.seeder_service import SeederService
from marvin.schemas.group.group import GroupCreate, GroupRead
from marvin.services.group.group_service import GroupService

PROJECT_DIR = Path(__file__).parent.parent.parent

logger = root_logger.get_logger()


def init_plugin_db(session: orm.Session, plugins: AppPlugins) -> None:
    """
    Initialize the database for all registered and enabled plugins.

    This function is called after the main application database has been initialized
    and migrated. It iterates through loaded plugins and calls their respective
    `init_db` functions if they exist.

    Args:
        session (orm.Session): The active SQLAlchemy session.
        plugins (AppPlugins): An AppPlugins instance containing loaded plugins.
    """
    settings = get_app_settings()
    if settings.PLUGINS:
        logger.info("-------Plugins: Init DB-------")
        for plugin_name, plugin in plugins.LOADED_PLUGINS.items():
            logger.debug(f"-------Initializing Plugin DB: {plugin_name}-------")
            plugin_dir = Path(os.path.dirname(plugin.__file__))
            plugin_db_path = str(plugin_dir / "db" / "init_db.py")

            if os.path.isfile(plugin_db_path):
                logger.debug(f"-------Loading Plugin DB: {plugin_name}-------")
                plugin.init_db(session)
            else:
                logger.debug(f"-------Plugin: Init_db not found: {plugin_name}-------")


def init_db(session: orm.Session) -> None:
    """
    Initializes the main application database with default data.

    This includes creating a default group, a default admin user, and seeding
    initial notifier options.

    Args:
        session (orm.Session): The active SQLAlchemy session.
    """
    settings = get_app_settings()

    instance_repos = get_repositories(session)

    default_group = default_group_init(instance_repos, settings._DEFAULT_GROUP)
    group_repos = get_repositories(session, group_id=default_group.id)
    default_user_init(group_repos)

    seeder_service = SeederService(group_repos)
    seeder_service.seed_notifier_options("notification_options")


def default_group_init(repos: AllRepositories, name: str) -> GroupRead:
    """
    Creates the default group if it doesn't already exist.

    Args:
        repos (AllRepositories): The repository accessor for database operations.
        name (str): The name for the default group.

    Returns:
        GroupRead: The created or existing default group.
    """
    logger.info("Generating Default Group")
    return GroupService.create_group(repos, GroupCreate(name=name))


def safe_try(func: Callable) -> None:
    """
    Executes a function and logs any exceptions without raising them.

    Args:
        func (Callable): The function to execute.
    """
    try:
        func()
    except Exception as e:
        logger.error(f"Error calling '{func.__name__}': {e}")


def connect(session: orm.Session) -> bool:
    """
    Checks if a connection can be established to the database.

    Args:
        session (orm.Session): The SQLAlchemy session to use for the connection test.

    Returns:
        bool: True if the connection is successful, False otherwise.
    """
    try:
        session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return False


def include_name(name: str, type_: str, parent_names: dict[str, Any]) -> bool:
    """
    Alembic include_name hook to filter tables during autogeneration.

    This function is used by Alembic to decide which database objects should be
    considered when generating migration scripts. It ensures that tables not
    defined in the main SQLAlchemy metadata or plugin metadata (identified by
    a prefix) are ignored, preventing accidental dropping of unknown tables.

    Args:
        name (str): The name of the database object (e.g., table name).
        type_ (str): The type of the database object (e.g., "table", "column").
        parent_names (dict[str, Any]): A dictionary of parent object names.

    Returns:
        bool: True if the object should be included, False otherwise.
    """
    # TODO: This function relies on global `target_metadata` and `PLUGIN_PREFIX`
    # which are not defined in this file. This might indicate a refactoring need
    # or that these are expected to be globally available in the Alembic context.
    # For now, assuming they are available in the execution scope of Alembic.
    if type_ == "table":
        # Dynamically get target_metadata and PLUGIN_PREFIX if possible, or log a warning
        try:
            # This is a placeholder for how these might be accessed.
            # The actual mechanism might be different in Alembic's execution context.
            from marvin.db.models import Base  # Assuming Base has the metadata
            target_metadata = Base.metadata
            # PLUGIN_PREFIX would likely come from settings or another global config
            settings = get_app_settings()
            PLUGIN_PREFIX = settings.PLUGIN_PREFIX
            return name in target_metadata.tables or name.startswith(PLUGIN_PREFIX)
        except ImportError:
            logger.warning("Could not import Base for target_metadata in include_name hook.")
            # Fallback or stricter behavior might be needed
            return False # Or True, depending on desired safety if metadata can't be checked
    return True


def db_is_at_head(alembic_cfg: config.Config) -> bool:
    """
    Checks if the database is migrated to the latest Alembic revision (head).

    Args:
        alembic_cfg (config.Config): The Alembic configuration object.

    Returns:
        bool: True if the database is at the head revision, False otherwise.

    Raises:
        ValueError: If the database URL is not configured.
    """
    settings = get_app_settings()
    url = settings.DB_URL
    if not url:
        raise ValueError("No database url found")

    connectable = engine.create_engine(url) # Note: global `engine` is used here
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


def main() -> None:
    """
    Main database initialization and migration function.

    This function performs the following steps:
    1. Waits for a successful database connection.
    2. Gathers Alembic configuration paths for the main app and all plugins.
    3. For each Alembic configuration:
        - Sets up plugin-specific script locations and version tables if needed.
        - Checks if the database is at the latest revision.
        - If not, runs `alembic upgrade head`.
    4. Creates PostgreSQL extensions if using PostgreSQL.
    5. Applies any data fixes using `fix_migration_data`.
    6. If the database is new (no users), initializes it with `init_db`.
    7. Initializes plugin databases using `init_plugin_db`.

    Raises:
        ConnectionError: If the database connection cannot be established after multiple retries.
        Exception: If an Alembic configuration file path is invalid.
    """
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
            logger.debug("Main Databse exists")
        else:
            logger.info("Main Database contains no users initializing...")
            init_db(session)

        init_plugin_db(session, plugins)
