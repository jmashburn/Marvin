from abc import ABC, abstractmethod
from pathlib import Path

from marvin.core.root_logger import get_logger
from marvin.repos.repository_factory import AllRepositories


class AbstractSeeder(ABC):
    """
    Abstract class for seeding the database.
    """

    def __init__(self, db: AllRepositories):
        self.db = db
        self.logger = get_logger("Data Seeder")
        self.resources = Path(__file__).parent / "resources"

    @abstractmethod
    def _seed(self, path: str | None = None) -> None: ...
