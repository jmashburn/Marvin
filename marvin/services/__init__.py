from marvin.core.config import get_app_dirs, get_app_plugins, get_app_settings
from marvin.core.root_logger import get_logger


class BaseService:
    def __init__(self) -> None:
        self._logger = get_logger()
        self._settings = get_app_settings()
        self._directories = get_app_dirs()
        self._plugins = get_app_plugins()
