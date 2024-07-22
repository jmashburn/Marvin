import os
from collections.abc import Callable
from pathlib import Path
from time import sleep

from alembic import command, config, script
from alembic.config import Config
from alembic.runtime import migration
from sqlalchemy import engine, orm, text
from marvin.core import root_logger
from marvin.core.config import get_app_settings
from marvin.db.db_setup import session_context
from marvin.repos.all_repositories import get_repositories
from marvin.repos.repository_factory import AllRepositories

PROJECT_DIR = Path(__file__).parent.parent.parent

logger = root_logger.get_logger()


def init_db(db: AllRepositories) -> None:
    pass


def default_group_init(db: AllRepositories):
    pass


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


def db_is_at_head(alembic_cfg: config.Config) -> bool:
    settings = get_app_settings()
    url = settings.DB_URL

    if not url:
        raise ValueError("No database url found")

    connectable = engine.create_engine(url)
    directory = script.ScriptDirectory.from_config(alembic_cfg)
    with connectable.begin() as connection:
        context = migration.MigrationContext.configure(connection)
        return set(context.get_current_heads()) == set(directory.get_heads())


def main():
    max_retry = 10
    wait_second = 1

    with session_context() as session:
        while True:
            if connect(session):
                logger.info("Database connection established.")
                break

            logger.error(f"Database connection failed - exiting application.")
            max_retry -= 1

            sleep(wait_second)

            if max_retry == 0:
                raise ConnectionError("Database connection failed - exiting application.")

        alembic_cfg_path = os.getenv("ALEMBIC_CONFIG_FILE", default=str(PROJECT_DIR / "alembic.ini"))

        if not os.path.isfile(alembic_cfg_path):
            raise Exception("Provided alembic config path doesn't exist")

        alembic_cfg = Config(alembic_cfg_path)
        if db_is_at_head(alembic_cfg):
            logger.debug("Migration not needed")
        else:
            logger.info("Migration needed. Performing migration...")
            command.upgrade(alembic_cfg, "head")

        if session.get_bind().name == "postgresql":
            session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

        db = get_repositories(session)
        # safe_try(lambda: fix_migration_data(session))

        # if db.users.get_all():
        #     logger.debug("Databse exists")
        # else:
        #     logger.info("Database contains no users initializing...")
        #     init_db(db)
