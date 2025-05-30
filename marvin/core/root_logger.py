"""
This module provides a centralized logging setup for the Marvin application.

It initializes and configures a root logger based on the application settings
and environment (development, testing, or production). Modules can then obtain
logger instances from this root logger.
"""

import logging

from .config import get_app_dirs, get_app_settings
from .logger.config import configured_logger

__root_logger: None | logging.Logger = None


def get_logger(module=None) -> logging.Logger:
    """
    Get a logger instance from a module
    """
    global __root_logger

    if __root_logger is None:
        app_settings = get_app_settings()

        mode = "development"

        if app_settings.TESTING:
            mode = "testing"
        elif app_settings.PRODUCTION:
            mode = "production"

        dirs = get_app_dirs()

        substitutions = {"DATA_DIR": dirs.DATA_DIR.as_posix(), "LOG_LEVEL": app_settings.LOG_LEVEL.upper()}

        __root_logger = configured_logger(mode=mode, config_override=app_settings.LOG_CONFIG_OVERRIDE, substitutions=substitutions)

    if module is None:
        return __root_logger

    return __root_logger.getChild(module)
