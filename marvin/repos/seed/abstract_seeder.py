from abc import ABC, abstractmethod
from logging import Logger
from pathlib import Path

from marvin.core.root_logger import get_logger
from marvin.repos.repository_factory import AllRepositories
from marvin.core.config import get_app_settings, get_app_dirs


class AbstractSeeder(ABC):
    """
    Abstract class for seeding the database.
    """

    def __init__(self, db: AllRepositories, logger: Logger | None = None):
        self.db = db
        self.logger = logger or get_logger("Data Seeder")
        self.resources = Path(__file__).parent / "resources"
        self.settings = get_app_settings()
        self.directories = get_app_dirs()

    @abstractmethod
    def _seed(self, path: str | None = None) -> None: ...
