import logging
import secrets
from collections import OrderedDict
from pathlib import Path


from datetime import datetime, timezone
from typing import NamedTuple
from dotenv import dotenv_values
from dateutil.tz import tzlocal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .db_providers import AbstractDBProvider, db_provider_factory


class ScheduleTime(NamedTuple):
    hour: int
    minute: int


def determine_secrets(data_dir: Path, production: bool) -> str:
    if not production:
        return "ssh-secret-test-key"

    secrets_file = data_dir.joinpath(".secret")
    if secrets_file.is_file():
        with open(secrets_file) as f:
            return f.read()
    else:
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(secrets_file, "w") as f:
            new_secret = secrets.token_hex(32)
            f.write(new_secret)
        return new_secret


class AppSettings(BaseSettings):
    PRODUCTION: bool = False

    BASE_URL: str = "http://localhost:8080"
    """trailing slashes are trimmed (ex. `http://localhost:8080/` becomes ``http://localhost:8080`)"""

    API_DOCS: bool = True

    SECRET: str

    ENV_SECRETS: OrderedDict | None = None

    PLUGIN_PREFIX: str = "marvin_"
    PLUGINS: bool = True

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080

    LOG_CONFIG_OVERRIDE: Path | None = None
    """ path to custom logging configuration file"""

    LOG_LEVEL: str = "info"
    """ corresponds to standard Python Log levels """

    _logger: logging.Logger | None = None

    DAILY_SCHEDULE_TIME: str = "23:45"
    """Local server time, in HH:MM format. See `DAILY_SCHEDULE_TIME_UTC` for the parsed UTC equivalent"""

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            from marvin.core.root_logger import get_logger

            self._logger = get_logger()

        return self._logger

    @property
    def DAILY_SCHEDULE_TIME_UTC(self) -> ScheduleTime:
        """The DAILY_SCHEDULE_TIME in UTC, parsed into hours and minutes"""

        # parse DAILY_SCHEDULE_TIME into hours and minutes
        try:
            hour_str, minute_str = self.DAILY_SCHEDULE_TIME.split(":")
            local_hour = int(hour_str)
            local_minute = int(minute_str)
        except ValueError:
            local_hour = 23
            local_minute = 45
            self.logger.exception(
                f"Unable to parse {self.DAILY_SCHEDULE_TIME=} as HH:MM; defaulting to {local_hour}:{local_minute}"
            )

        # DAILY_SCHEDULE_TIME is in local time, so we convert it to UTC
        local_tz = tzlocal()

        now = datetime.now(local_tz)
        local_time = now.replace(hour=local_hour, minute=local_minute)
        utc_time = local_time.astimezone(timezone.utc)

        self.logger.debug(f"Local time: {local_hour}:{local_minute} | UTC time: {utc_time.hour}:{utc_time.minute}")
        return ScheduleTime(utc_time.hour, utc_time.minute)

    # ===============================================
    # Testing Config

    TESTING: bool = False

    model_config = SettingsConfigDict(arbitrary_types_allowed=True, extra="allow")

    @field_validator("BASE_URL")
    @classmethod
    def remove_trailing_slash(cls, v: str) -> str:
        if v and v[-1] == "/":
            return v[:-1]

        return v

    @property
    def DOCS_URL(self) -> str | None:
        return "/docs" if self.API_DOCS else None

    @property
    def REDOC_URL(self) -> str | None:
        return "/redoc" if self.API_DOCS else None

    # ===============================================
    # Database Config

    DB_ENGINE: str = "sqlite"
    DB_PROVIDER: AbstractDBProvider | None = None

    @property
    def DB_URL(self) -> str | None:
        return self.DB_PROVIDER.db_url if self.DB_PROVIDER else None

    @property
    def DB_URL_PUBLIC(self) -> str | None:
        return self.DB_PROVIDER.db_url_public if self.DB_PROVIDER else None


class PluginSettings(BaseSettings):
    """Plugin Settings"""

    # Plugin Name
    PLUGIN_NAME: str

    # Plugin Version
    PLUGIN_VERSION: str

    # Plugin Description
    PLUGIN_DESCRIPTION: str | None = None

    # Plugin Author
    PLUGIN_AUTHOR: str | None = None

    # Plugin Author Email
    PLUGIN_AUTHOR_EMAIL: str | None = None

    model_config = SettingsConfigDict(arbitrary_types_allowed=True, extra="allow")


def app_settings_constructor(
    data_dir: Path,
    production: bool,
    env_file: Path,
    env_secrets: Path,
    secrets_dir: Path,
    env_encoding="utf-8",
) -> AppSettings:
    """
    app_settings_constructor is a factor function that returns an AppSettings object.
    Its is used to inject the dependencies
    into the AppSettings objects and nested child objects.
    AppSettings should not be substantianed directory, but rather
    through this factory function
    """

    app_settings = AppSettings(
        _env_file=env_file,  # type: ignore
        _env_file_encoding=env_encoding,  # type: ignore
        _secrets_dir=secrets_dir,  # type: ignore
        **{"SECRET": determine_secrets(data_dir, production)},
        **{"ENV_SECRETS": dotenv_values(env_secrets)},
    )

    app_settings.DB_PROVIDER = db_provider_factory(
        app_settings.DB_ENGINE or "sqlite",
        data_dir,
        env_file=env_file,
        env_encoding=env_encoding,
    )
    return app_settings


def app_plugin_settings_constructor(
    name: str,
    version: str,
    env_file: Path,
    data_dir: Path,
    production: bool,
    env_secrets: Path,
    secrets_dir: Path,
    env_encoding="utf-8",
    description: str | None = None,
    author: str | None = None,
    author_email: str | None = None,
    env_nested_delimiter: str = "__",
    PluginSettings: type[PluginSettings] = PluginSettings,
) -> PluginSettings:
    app_settings = PluginSettings(
        PLUGIN_NAME=name,
        PLUGIN_VERSION=version,
        PLUGIN_DESCRIPTION=description,
        PLUGIN_AUTHOR=author,
        PLUGIN_AUTHOR_EMAIL=author_email,
        _env_prefix=name.upper() + "_",
        _env_file=env_file,  # type: ignore
        _env_file_encoding=env_encoding,  # type: ignore
        _secrets_dir=secrets_dir,  # type: ignore
        _env_nested_delimiter=env_nested_delimiter,
        **{"SECRET": determine_secrets(data_dir, production)},
        **{"ENV_SECRETS": dotenv_values(env_secrets)},
    )

    return app_settings
