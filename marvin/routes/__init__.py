from collections.abc import Callable

from fastapi import APIRouter

from marvin.core.config import get_app_plugins, get_app_settings
from marvin.core.root_logger import get_logger

from . import app
from . import auth
from . import groups
from . import users

settings = get_app_settings()
logger = get_logger()

# load Core api Routes
router = APIRouter(prefix="/api")
router.include_router(app.router)
router.include_router(auth.router)
router.include_router(groups.router)
router.include_router(users.router)


# Load Plugins. Plugins dir takes precendent the lib plugins
def load_routes():
    """Load Plugins from plugins"""
    for plugin_name, plugin in plugins.LOADED_PLUGINS.items():
        if "routers" in plugin.__dir__():
            if isinstance(plugin.routers, Callable):
                logger.info(f"Loaded Routers - name: {plugin_name} -- version: {plugin.__meta__['version']}")
                routers = plugin.routers()
                router.include_router(routers)


if settings.PLUGINS:
    logger.info("-------Plugins Enabled-------")
    plugins = get_app_plugins(settings.PLUGIN_PREFIX)
    load_routes()
