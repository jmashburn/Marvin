"""
This module defines the directory structure used by the Marvin application.

It includes the `AppDirectories` class, which centralizes the paths for
various application directories like data, plugins, backups, etc.
"""

from pathlib import Path


class AppDirectories:
    """
    Manages the directory structure for the Marvin application.

    Attributes:
        DATA_DIR (Path): The main data directory.
        PLUGIN_DIR (Path): The directory for plugins.
        BACKUP_DIR (Path): The directory for backups.
        SEED_DIR (Path): The directory for seed data.
        TEMP_DIR (Path): The directory for temporary files.
    """

    def __init__(self, data_dir: Path, plugin_dir: Path) -> None:
        """
        Initializes the AppDirectories instance and ensures directories exist.

        Args:
            data_dir (Path): The root data directory for the application.
            plugin_dir (Path): The root plugin directory for the application.
        """
        self.DATA_DIR = data_dir
        self.PLUGIN_DIR = plugin_dir
        self.BACKUP_DIR = data_dir.joinpath("backups")
        self.TEMPLATE_DIR = data_dir.joinpath("templates")
        self.SEED_DIR = data_dir.joinpath("seeds")
        self._TEMP_DIR = data_dir.joinpath(".temp")
        self.ensure_directories()

    @property
    def TEMP_DIR(self) -> Path:
        """Returns the path to the temporary directory."""
        return self._TEMP_DIR

    def ensure_directories(self) -> None:
        """
        Ensures that all required application directories exist.

        Creates the directories if they don't already exist.
        """
        required_dirs = [self.BACKUP_DIR, self.PLUGIN_DIR, self.TEMPLATE_DIR, self.SEED_DIR, self.TEMP_DIR]
        for dir_path in required_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
