"""
This module handles the loading and management of plugins for the Marvin application.

It defines the `AppPlugins` class, which is responsible for discovering,
importing, and providing access to plugins located in a specified directory.
"""

import importlib
import pkgutil
import sys
from pathlib import Path
from types import ModuleType


class AppPlugins:
    """
    Manages application plugins.

    This class discovers and loads plugins from a specified directory that match
    a given prefix. It provides access to the loaded plugins.
    """

    def __init__(self, plugin_dir: Path, plugin_prefix: str) -> None:
        """
        Initializes the AppPlugins manager.

        Args:
            plugin_dir (Path): The directory to search for plugins.
            plugin_prefix (str): The prefix that plugin module names should have.
        """
        sys.path.insert(0, str(plugin_dir))
        self._PLUGIN_DIR: list[str] = sys.path  # Stores the modified sys.path

        self._PLUGIN_PREFIX: str = plugin_prefix
        self._LOADED_PLUGINS: dict[str, ModuleType] = self._load_plugins()

    @property
    def PLUGIN_DIR(self) -> list[str]:
        """
        Returns the system path list, which includes the plugin directory.
        """
        return self._PLUGIN_DIR

    @property
    def PLUGIN_PREFIX(self) -> str:
        """
        Returns the prefix used to identify plugin modules.
        """
        return self._PLUGIN_PREFIX

    @property
    def LOADED_PLUGINS(self) -> dict[str, ModuleType]:
        """
        Returns a dictionary of loaded plugins, where keys are module names
        and values are the imported module objects.
        """
        return self._LOADED_PLUGINS

    def _import_module(self, module_name: str) -> ModuleType:
        """
        Imports a module by its name from the plugin directory.

        Args:
            module_name (str): The name of the module to import.

        Returns:
            ModuleType: The imported module.
        """
        return importlib.import_module(module_name)

    def _load_plugins(self) -> dict[str, ModuleType]:
        """
        Discovers and loads plugins from the plugin directory.

        Plugins are identified by the `PLUGIN_PREFIX`. A module is considered
        a valid plugin if it starts with the prefix and contains a `__meta__`
        attribute with "name" and "version" keys.

        Returns:
            dict[str, ModuleType]: A dictionary of loaded plugins.
        """
        loaded_apps: dict[str, ModuleType] = {}
        # Iterate over modules in the (modified) sys.path
        for _, module_name, _ in pkgutil.iter_modules():
            if module_name.startswith(self.PLUGIN_PREFIX):
                module = self._import_module(module_name)
                # Check for __meta__ attribute and required keys for a valid plugin
                if hasattr(module, "__meta__") and isinstance(module.__meta__, dict) and "name" in module.__meta__ and "version" in module.__meta__:
                    loaded_apps[module_name] = module
        return loaded_apps
