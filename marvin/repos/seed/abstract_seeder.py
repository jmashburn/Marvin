"""
This module defines the abstract base class for database seeders.

It provides the `AbstractSeeder` class, which outlines the common interface
and initialization for all seeder implementations used to populate the
database with initial or sample data.
"""
from abc import ABC, abstractmethod
from logging import Logger
from pathlib import Path

from marvin.core.config import get_app_dirs, get_app_settings
from marvin.core.root_logger import get_logger
from marvin.repos.repository_factory import AllRepositories


class AbstractSeeder(ABC):
    """
    Abstract base class for database seeders.

    Seeder classes are responsible for populating the database with initial
    or sample data. This class provides a common structure and initialization
    for all seeders.
    """

    def __init__(self, db: AllRepositories, logger: Logger | None = None):
        """
        Initializes the AbstractSeeder.

        Args:
            db (AllRepositories): An instance of `AllRepositories` providing
                                  access to all data repositories.
            logger (Logger | None, optional): A logger instance. If None,
                                              a new logger named "Data Seeder"
                                              is created. Defaults to None.
        """
        self.repos = db  # Provides access to all data repositories.
        self.logger = logger or get_logger("Data Seeder")  # Logger for seeder activities.
        # Path to the 'resources' directory, typically containing data files for seeding (e.g., JSON, CSV).
        self.resources: Path = Path(__file__).parent / "resources"
        self.settings = get_app_settings()  # Access to application settings.
        self.directories = get_app_dirs()  # Access to application directory structure.

    @abstractmethod
    def seed(self, path: str | None = None) -> None:
        """
        Abstract method to perform the seeding operation.

        Subclasses must implement this method to define how specific data
        is created and inserted into the database.

        Args:
            path (str | None, optional): An optional path or identifier,
                                         potentially to a specific data file or
                                         subset of data to seed. Defaults to None.
        """
        ... # Ellipsis indicates that the method must be implemented by subclasses.
