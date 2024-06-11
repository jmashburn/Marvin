import secrets
from typing import OrderedDict
from dotenv import dotenv_values
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def determine_secrets(data_dir: Path, production: bool) -> str:
    if not production:
        return "ssh-secret-test-kkey"

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
    PRODUCTION: bool

    BASE_URL: str = "http://localhost:8080"
    """trailing slashes are trimmed (ex. `http://localhost:8080/` becomes ``http://localhost:8080`)"""

    API_DOCS: bool = True

    SECRET: str

    ENV_SECRETS: OrderedDict | None = None

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 9000

    LOG_CONFIG_OVERRIDE: Path | None = None
    """ path to custom logging configuration file"""

    LOG_LEVEL: str = "info"
    """ corresponds to standard Python Log levels """

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


def app_settings_constructor(
    data_dir: Path, production: bool, env_file: Path, env_secrets: Path, env_encoding="utf-8"
) -> AppSettings:
    """
    app_settings_constructor is a factor function that returns an AppSettings object.  Its is ued to inject the dependencies
    into the AppSettings objects and nested child objects. AppSettings should not be substantianed directory, but rather
    through this factory function
    """

    app_settings = AppSettings(
        _env_file=env_file,  # type: ignore
        _env_file_encoding=env_encoding,  # type: ignore
        **{"SECRET": determine_secrets(data_dir, production)},
        **{"ENV_SECRETS": dotenv_values(env_secrets)},
    )

    return app_settings
