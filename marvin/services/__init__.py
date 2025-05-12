from marvin.core.config import get_app_dirs, get_app_plugins, get_app_settings
from marvin.core.root_logger import get_logger


class BaseService:
    def __init__(self) -> None:
        self.logger = get_logger()
        self.settings = get_app_settings()
        self.directories = get_app_dirs()
        self.plugins = get_app_plugins()
