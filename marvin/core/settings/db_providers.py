from abc import ABC, abstractmethod
from pathlib import Path
from urllib import parse as urlparse

from pydantic import BaseModel, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class AbstractDBProvider(ABC):
    @property
    @abstractmethod
    def db_url(self) -> str: ...

    @property
    @abstractmethod
    def db_url_public(self) -> str: ...


class SQLiteProvider(AbstractDBProvider, BaseModel):
    data_dir: Path
    name: str = "marvin.db"
    prefix: str = ""

    @property
    def db_path(self):
        return self.data_dir / f"{self.prefix}{self.name}"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{str(self.db_path.absolute())}"

    @property
    def db_url_public(self) -> str:
        return self.db_url


class PostgresProvider(AbstractDBProvider, BaseSettings):
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_SERVER: str = ""
    POSTGRES_PORT: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_URL_OVERRIDE: str | None = None

    model_config = SettingsConfigDict(arbitrary_types_allowed=True, extra="allow")

    @property
    def db_url(self) -> str:
        if self.POSTGRES_URL_OVERRIDE:
            url = self.POSTGRES_URL_OVERRIDE

            schema, remainder = url.split("://", 1)
            if schema != "postgres":
                raise ValueError("POSTGRES_URL_OVERRIDE schema must be postgresql")

            remainder = remainder.split(":", 1)[1]
            password = remainder[: remainder.rfind("@")]
            quoted_password = urlparse.quote(password)

            safe_url = url.replace(password, quoted_password)

            return safe_url
        return str(
            PostgresDsn.build(
                schema="postgresql",
                username=self.POSTGRES_USER,
                password=urlparse.quote(self.POSTGRES_PASSWORD),
                host=f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}",
                path=f"{self.POSTGRES_DB or ''}",
            )
        )

    @property
    def db_url_public(self) -> str:
        user = self.POSTGRES_USER
        password = self.POSTGRES_PASSWORD
        return self.db_url.replace(user, "*********", 1).replace(password, "***********", 1)


def db_provider_factory(provider_name: str, data_dir: Path, env_file: Path, env_encoding="utf-8") -> AbstractDBProvider:
    if provider_name == "postgres":
        return PostgresProvider(_env_file=env_file, _env_file_encoding=env_encoding)
    return SQLiteProvider(data_dir=data_dir)
