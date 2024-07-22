import importlib
import pkgutil
import sys
from pathlib import Path


class AppPlugins:
    def __init__(self, plugin_dir: Path, plugin_prefix: str) -> None:
        sys.path.insert(0, str(plugin_dir))
        self._PLUGIN_DIR = sys.path

        self._PLUGIN_PREFIX = plugin_prefix

        self._LOADED_PLUGINS = self.load_plugins()

    @property
    def PLUGIN_DIR(self):
        return self._PLUGIN_DIR

    @property
    def PLUGIN_PREFIX(self):
        return self._PLUGIN_PREFIX

    @property
    def LOADED_PLUGINS(self):
        return self._LOADED_PLUGINS

    def import_module(self, module_name):
        """Import a module by its name from plugins folder"""
        module = module_name
        return importlib.import_module(module)

    def load_plugins(self) -> list:
        """Import Plugins from plugins folder"""
        loaded_apps = []
        for _, application, _ in pkgutil.iter_modules():
            if application.startswith(self.PLUGIN_PREFIX):
                module = self.import_module(application)
                if hasattr(module, "__meta__") and "name" in module.__meta__ and "version" in module.__meta__:
                    loaded_apps.append(module)
        return loaded_apps
