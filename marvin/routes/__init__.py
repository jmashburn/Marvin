from fastapi import APIRouter


from marvin.core.config import get_app_plugins, get_app_settings
from marvin.core.root_logger import get_logger

from . import app

settings = get_app_settings()
logger = get_logger()

# load Core api Routes
router = APIRouter(prefix="/api")
router.include_router(app.router)


# Load Plugins. Plugins dir takes precendent the lib plugins
def load_routes():
    """Load Plugins from plugins"""
    for plugin in plugins.LOADED_PLUGINS:
        if "routers" in plugin.__dir__():
            logger.info(f"Loaded Routers - name: {plugin.__meta__['name']} -- version: {plugin.__meta__['version']}")
            router.include_router(plugin.routers)


if settings.PLUGINS:
    logger.info("-------Plugins Enabled-------")
    plugins = get_app_plugins(settings.PLUGIN_PREFIX)
    load_routes()
