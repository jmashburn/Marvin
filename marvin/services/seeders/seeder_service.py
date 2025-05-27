"""
This module defines the `SeederService`, which is responsible for orchestrating
database seeding operations within the Marvin application.

It uses specific seeder classes (e.g., `NotifierOptionSeeder`) to populate
the database with initial or default data for various parts of the application.
"""

from marvin.repos.repository_factory import AllRepositories  # For accessing data repositories
from marvin.repos.seed.seeders import NotifierOptionSeeder  # Specific seeder for notifier options

# The line `# $from marvin.repos.seeders` seems like a placeholder or an artifact;
# actual seeder classes are imported directly.
from marvin.services import BaseService  # Base service class for common functionalities


class SeederService(BaseService):
    """
    Service layer for coordinating database seeding operations.

    This service instantiates and calls appropriate seeder classes to populate
    the database with initial data, such as default notifier options.
    It relies on an `AllRepositories` instance for database access passed to the seeders.
    """

    def __init__(self, repos: AllRepositories) -> None:
        """
        Initializes the SeederService.

        Args:
            repos (AllRepositories): An instance of `AllRepositories` providing
                                     access to all data repositories needed by the seeders.
        """
        super().__init__()  # Initialize BaseService (likely for settings, logger)
        self.repos: AllRepositories = repos
        """Provides access to all data repositories, passed to individual seeders."""
        # self.logger is inherited from BaseService.

    def seed_notifier_options(self, name: str | None = None) -> None:
        """
        Seeds the database with event notifier options.

        Instantiates `NotifierOptionSeeder` and calls its `seed` method.
        The `name` parameter can specify a particular configuration or data file
        for the seeder to use.

        Args:
            name (str | None, optional): The name of the seeder configuration or
                                         data file to use (e.g., "notifier_options").
                                         Passed to the seeder's `seed` method.
                                         If None, the seeder might use a default.
        """
        self._logger.info(f"Initiating seeding of notifier options with configuration: '{name or 'default'}'")
        # Instantiate the specific seeder for notifier options
        notifier_seeder = NotifierOptionSeeder(db=self.repos, logger=self._logger)
        # Execute the seed operation
        notifier_seeder.seed(name)
        self._logger.info(f"Completed seeding of notifier options for configuration: '{name or 'default'}'")
