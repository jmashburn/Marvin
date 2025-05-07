import os
from functools import lru_cache
from pathlib import Path

import dotenv

from marvin.core.settings import app_plugin_settings_constructor, app_settings_constructor

from .settings import AppDirectories, AppPlugins, AppSettings, PluginSettings

CWD = Path(__file__).parent
BASE_DIR = CWD.parent.parent
ENV = BASE_DIR.joinpath(".env")
ENV_SECRETS = BASE_DIR.joinpath(".env.secrets")

dotenv.load_dotenv(ENV)
PRODUCTION = os.getenv("PRODUCTION", "False") == "True"
TESTING = os.getenv("TESTING", "False") == "True"
DATA_DIR = os.getenv("DATA_DIR")
PLUGIN_DIR = os.getenv("PLUGIN_DIR")
SECRECTS_DIR = os.getenv("SECRETS_DIR")


def determine_data_dir() -> Path:
    global PRODUCTION, TESTING, BASE_DIR, DATA_DIR

    if TESTING:
        return BASE_DIR.joinpath(DATA_DIR if DATA_DIR else "tests", ".temp")

    if PRODUCTION:
        ## Make sure Path is absoulte
        return Path(DATA_DIR if DATA_DIR else BASE_DIR.joinpath("app", "data"))

    return BASE_DIR.joinpath("dev", "data")


def determin_plugin_dir() -> Path:
    global PRODUCTION, TESTING, BASE_DIR, DATA_DIR

    if TESTING:
        return BASE_DIR.joinpath(DATA_DIR if DATA_DIR else "tests", ".temp")
    if PRODUCTION:
        return Path(DATA_DIR if DATA_DIR else BASE_DIR.joinpath("app", "plugins"))

    return BASE_DIR.joinpath("dev", "plugins")


@lru_cache
def get_app_dirs() -> AppDirectories:
    return AppDirectories(determine_data_dir(), determin_plugin_dir())


@lru_cache
def get_app_settings(name: str | None = None) -> AppSettings:
    return app_settings_constructor(
        env_file=ENV,
        env_secrets=ENV_SECRETS,
        secrets_dir=SECRECTS_DIR,
        production=PRODUCTION,
        data_dir=determine_data_dir(),
    )


@lru_cache
def get_app_plugin_settings(
    name: str,
    version: str,
    description: str | None = None,
    author: str | None = None,
    author_email: str | None = None,
    env_file: Path | None = ENV,
    env_secrets: str | None = ENV_SECRETS,
    secrets_dir: str | None = SECRECTS_DIR,
    PluginSettings: type[PluginSettings] = PluginSettings,
) -> PluginSettings:
    return app_plugin_settings_constructor(
        name=name,
        version=version,
        description=description,
        author=author,
        author_email=author_email,
        env_file=env_file,
        env_secrets=env_secrets,
        secrets_dir=secrets_dir,
        production=PRODUCTION,
        data_dir=determine_data_dir(),
        PluginSettings=PluginSettings,
    )


@lru_cache
def get_app_plugins(plugin_prefix: str) -> AppPlugins:
    return AppPlugins(determin_plugin_dir(), plugin_prefix)
