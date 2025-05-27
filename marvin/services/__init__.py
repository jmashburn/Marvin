"""
This module serves as the entry point for the `marvin.services` package.

It defines the `BaseService` class, which provides common functionalities and
attributes (like logger, settings, and directory configurations) intended to be
inherited by all other service classes within this package. This promotes
consistency and reduces boilerplate in concrete service implementations.
"""

from logging import Logger  # For type hinting the logger attribute

# Marvin core components for accessing application-wide configurations and utilities
from marvin.core.config import AppDirectories, AppSettings, get_app_dirs, get_app_settings

# get_app_plugins was imported but not used in BaseService.
# from marvin.core.config import get_app_plugins
from marvin.core.root_logger import get_logger  # For obtaining a logger instance


class BaseService:
    """
    A base class for all service layer classes in the Marvin application.

    This class provides common attributes that services might need, such as:
    - A logger instance for logging messages.
    - Access to application settings (`AppSettings`).
    - Access to application directory configurations (`AppDirectories`).

    Services inheriting from `BaseService` will automatically have these
    attributes initialized and available for use.
    """

    def __init__(self) -> None:
        """
        Initializes the BaseService.

        Sets up common attributes: `logger`, `settings`, and `directories` by
        calling their respective global accessor functions from `marvin.core`.
        """
        self._logger: Logger = get_logger()
        """A logger instance for service-specific logging."""
        self._settings: AppSettings = get_app_settings()
        """An instance of `AppSettings` providing access to application configuration."""
        self._directories: AppDirectories = get_app_dirs()
        """An instance of `AppDirectories` providing access to key application paths."""
