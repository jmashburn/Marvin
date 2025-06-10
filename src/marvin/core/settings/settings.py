"""
This module defines the main application settings for Marvin.

It includes Pydantic models for application settings (`AppSettings`) and plugin
settings (`PluginSettings`). It also provides helper classes and functions for
managing features, schedules, and sensitive data.

Settings are loaded from environment variables and .env files.
"""

import logging
import os
import secrets
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, NamedTuple

from dateutil.tz import tzlocal
from dotenv import dotenv_values
from pydantic import PlainSerializer, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .db_providers import AbstractDBProvider, db_provider_factory
from .theme import Theme


class ScheduleTime(NamedTuple):
    """
    Represents a specific time for scheduled tasks.

    Attributes:
        hour (int): The hour of the day (0-23).
        minute (int): The minute of the hour (0-59).
    """

    hour: int
    minute: int


class FeatureDetails(NamedTuple):
    """
    Represents the details of an application feature, including its status.

    Attributes:
        enabled (bool): Indicates if the feature is enabled or not.
        description (str | None): A short description explaining why the
                                 feature might be disabled or its current state.
    """

    enabled: bool
    """Indicates if the feature is enabled or not"""
    description: str | None
    """Short description describing why the feature is not ready"""

    def __str__(self) -> str:
        """Returns a string representation of the feature's status."""
        s = f"Enabled: {self.enabled}"
        if not self.enabled and self.description:
            s += f"\nReason: {self.description}"
        return s


MaskedNoneString = Annotated[
    str | None,
    PlainSerializer(lambda x: None if x is None else "*****", return_type=str | None),
]
"""
A Pydantic annotation for strings that should be masked (e.g., passwords)
when serialized, and also handles None values gracefully.
"""


def determine_secrets(data_dir: Path, production: bool) -> str:
    """
    Determines or generates the application's secret key.

    In non-production environments, a fixed test key is used.
    In production, it attempts to read the secret from a '.secret' file in the
    data directory. If the file doesn't exist, a new secret is generated and
    saved to the file.

    Args:
        data_dir (Path): The application's data directory.
        production (bool): Flag indicating if the application is in production mode.

    Returns:
        str: The application's secret key.
    """
    if not production:
        return "ssh-secret-test-key"  # Fixed secret for non-production

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
    """
    Main application settings.

    This class defines all configuration parameters for the Marvin application,
    loaded from environment variables and .env files. It uses Pydantic for
    data validation and management.
    """

    theme: Theme = Theme()
    """The application theme settings."""

    PRODUCTION: bool = False
    """Flag indicating if the application is running in production mode."""

    IS_DEMO: bool = False

    BASE_URL: str = "http://localhost:8080"
    """trailing slashes are trimmed (ex. `http://localhost:8080/` becomes ``http://localhost:8080`)"""

    API_DOCS: bool = True

    SECRET: str

    ENV_SECRETS: OrderedDict | None = None

    API_HOST: str = "0.0.0.0"

    API_PORT: int = 8080

    TOKEN_TIME: int = 48

    LOG_CONFIG_OVERRIDE: Path | None = None
    """ path to custom logging configuration file"""

    LOG_LEVEL: str = "info"
    """ corresponds to standard Python Log levels """

    _logger: logging.Logger | None = None

    DAILY_SCHEDULE_TIME: str = "23:47"
    """Local server time, in HH:MM format. See `DAILY_SCHEDULE_TIME_UTC` for the parsed UTC equivalent"""

    GITHUB_VERSION_URL: str = "https://github.com/jmashburn/Marvin/releases/latest"

    GIT_COMMIT_HASH: str = "unknown"

    ALLOW_SIGNUP: bool = False

    @property
    def logger(self) -> logging.Logger:
        """
        Provides a logger instance for the application.

        Initializes the root logger if it hasn't been already.

        Returns:
            logging.Logger: The application logger.
        """
        if self._logger is None:
            from marvin.core.root_logger import get_logger

            self._logger = get_logger()

        return self._logger

    @property
    def DAILY_SCHEDULE_TIME_UTC(self) -> ScheduleTime:
        """
        The `DAILY_SCHEDULE_TIME` converted to UTC and parsed into hours and minutes.

        The `DAILY_SCHEDULE_TIME` setting is expected to be in local server time.
        This property handles the conversion to UTC.

        Returns:
            ScheduleTime: The scheduled time in UTC.
        """

        # parse DAILY_SCHEDULE_TIME into hours and minutes
        try:
            hour_str, minute_str = self.DAILY_SCHEDULE_TIME.split(":")
            local_hour = int(hour_str)
            local_minute = int(minute_str)
        except ValueError:
            local_hour = 23
            local_minute = 45
            self.logger.exception(f"Unable to parse {self.DAILY_SCHEDULE_TIME=} as HH:MM; defaulting to {local_hour}:{local_minute}")

        # DAILY_SCHEDULE_TIME is in local time, so we convert it to UTC
        local_tz = tzlocal()

        now = datetime.now(local_tz)
        local_time = now.replace(hour=local_hour, minute=local_minute)
        utc_time = local_time.astimezone(UTC)

        self.logger.debug(f"Local time: {local_hour}:{local_minute} | UTC time: {utc_time.hour}:{utc_time.minute}")
        return ScheduleTime(utc_time.hour, utc_time.minute)
        # ===============================================

    # Security Configuration

    SECURITY_MAX_LOGIN_ATTEMPTS: int = 5

    SECURITY_USER_LOCKOUT_TIME: int = 24
    "time in hours"

    # ===============================================
    # Testing Config

    TESTING: bool = False

    model_config = SettingsConfigDict(arbitrary_types_allowed=True, extra="allow")

    @field_validator("BASE_URL")
    @classmethod
    def remove_trailing_slash(cls, v: str) -> str:
        """Pydantic validator to remove trailing slashes from the BASE_URL."""
        if v and v[-1] == "/":
            return v[:-1]

        return v

    @property
    def DOCS_URL(self) -> str | None:
        """URL for the FastAPI documentation (Swagger UI). Disabled if API_DOCS is False."""
        return "/docs" if self.API_DOCS else None

    @property
    def REDOC_URL(self) -> str | None:
        """URL for the ReDoc documentation. Disabled if API_DOCS is False."""
        return "/redoc" if self.API_DOCS else None

    # ===============================================
    # Database Config

    DB_ENGINE: str = "sqlite"
    """The database engine to use ('sqlite' or 'postgres')."""

    DB_PROVIDER: AbstractDBProvider | None = None
    """The database provider instance, configured by `app_settings_constructor`."""

    @property
    def DB_URL(self) -> str | None:
        """The full database connection URL. Returns None if DB_PROVIDER is not set."""
        return self.DB_PROVIDER.db_url if self.DB_PROVIDER else None

    @property
    def DB_URL_PUBLIC(self) -> str | None:
        """A public version of the database URL (credentials masked). Returns None if DB_PROVIDER is not set."""
        return self.DB_PROVIDER.db_url_public if self.DB_PROVIDER else None

    _DEFAULT_EMAIL: str = "changeme@example.com"
    """Default email for the initial admin user, if created."""

    _DEFAULT_PASSWORD: SecretStr = "MyPassword"
    """Default password for the initial admin user, if created."""

    _DEFAULT_GROUP: str = "Default"
    """Default group for the initial admin user, if created."""

    _DEFAULT_INTEGRATION_ID: str = "generic"
    """# Default identifier for integrations if not specified when creating an API token."""

    # ===============================================
    # Plugin Configurtion

    PLUGIN_PREFIX: str | None = "marvin_"

    @property
    def PLUGIN_ENABLED(self) -> bool:
        """Indicates if Plugin is configured and enabled."""
        return self.PLUGIN_FEATURE.enabled

    @property
    def PLUGIN_FEATURE(self) -> FeatureDetails:
        """Details about the PLUGIN feature status"""
        description = None
        required = {
            "PLUGIN_PREFIX": self.PLUGIN_PREFIX,
        }

        not_none = None not in required.values()
        if not not_none and not description:
            missing_values = [key for (key, value) in required.items() if value is None]
            description = f"Missing required values for {missing_values}"

        return FeatureDetails(
            enabled=not_none,
            description=description,
        )

    # ===============================================
    # Email Configuration

    _DEFAULT_EMAIL_TEMPLATE: str = "branded.html"
    """Default Email Template. place in templates folder"""
    SMTP_HOST: str | None = None
    """SMTP server hostname or IP address."""
    SMTP_PORT: str | None = "587"
    """SMTP server port."""
    SMTP_FROM_NAME: str | None = "Marvin"
    """The name to display in the 'From' field of emails."""
    SMTP_FROM_EMAIL: str | None = None
    """The email address to use in the 'From' field of emails."""
    SMTP_USER: MaskedNoneString = None
    """SMTP username for authentication (masked in logs/output)."""
    SMTP_PASSWORD: MaskedNoneString = None
    """SMTP password for authentication (masked in logs/output)."""
    SMTP_AUTH_STRATEGY: str | None = "TLS"
    """SMTP authentication strategy. Options: 'TLS', 'SSL', 'NONE'."""

    @property
    def SMTP_ENABLED(self) -> bool:
        """Indicates if SMTP is configured and enabled."""
        return self.SMTP_FEATURE.enabled

    @property
    def SMTP_FEATURE(self) -> FeatureDetails:
        """Details about the SMTP feature status, including validation."""
        return AppSettings.validate_smtp(
            self.SMTP_HOST,
            self.SMTP_PORT,
            self.SMTP_FROM_NAME,
            self.SMTP_FROM_EMAIL,
            self.SMTP_AUTH_STRATEGY,
            self.SMTP_USER,
            self.SMTP_PASSWORD,
        )

    @staticmethod
    def validate_smtp(
        host: str | None = None,
        port: str | None = None,
        from_name: str | None = None,
        from_email: str | None = None,
        strategy: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> FeatureDetails:
        """
        Validates that all necessary SMTP settings are provided.

        Args:
            host: SMTP host.
            port: SMTP port.
            from_name: SMTP from name.
            from_email: SMTP from email.
            strategy: SMTP authentication strategy.
            user: SMTP username.
            password: SMTP password.

        Returns:
            FeatureDetails: An object indicating if SMTP is enabled and a
                            description of any missing settings.
        """
        description = None
        required = {
            "SMTP_HOST": host,
            "SMTP_PORT": port,
            "SMTP_FROM_NAME": from_name,
            "SMTP_FROM_EMAIL": from_email,
            "SMTP_AUTH_STRATEGY": strategy,
        }
        missing_values = [key for (key, value) in required.items() if value is None]
        if missing_values:
            description = f"Missing required values for {missing_values}"

        if strategy and strategy.upper() in {"TLS", "SSL"}:
            required["SMTP_USER"] = user
            required["SMTP_PASSWORD"] = password
            if not description:
                missing_values = [key for (key, value) in required.items() if value is None]
                description = f"Missing required values for {missing_values} because SMTP_AUTH_STRATEGY is not None"

        not_none = "" not in required.values() and None not in required.values()

        return FeatureDetails(enabled=not_none, description=description)

    # ===============================================
    # LDAP Configuration

    LDAP_AUTH_ENABLED: bool = False
    LDAP_SERVER_URL: str | None = None
    LDAP_TLS_INSECURE: bool = False
    LDAP_TLS_CACERTFILE: str | None = None
    LDAP_ENABLE_STARTTLS: bool = False
    LDAP_BASE_DN: str | None = None
    LDAP_QUERY_BIND: str | None = None
    LDAP_QUERY_PASSWORD: MaskedNoneString = None
    LDAP_USER_FILTER: str | None = None
    LDAP_ADMIN_FILTER: str | None = None
    LDAP_ID_ATTRIBUTE: str = "uid"
    LDAP_MAIL_ATTRIBUTE: str = "mail"
    LDAP_NAME_ATTRIBUTE: str = "name"

    @property
    def LDAP_FEATURE(self) -> FeatureDetails:
        """Details about the LDAP feature status, including validation."""
        description = None if self.LDAP_AUTH_ENABLED else "LDAP_AUTH_ENABLED is false"
        required = {
            "LDAP_SERVER_URL": self.LDAP_SERVER_URL,
            "LDAP_BASE_DN": self.LDAP_BASE_DN,
            "LDAP_ID_ATTRIBUTE": self.LDAP_ID_ATTRIBUTE,
            "LDAP_MAIL_ATTRIBUTE": self.LDAP_MAIL_ATTRIBUTE,
            "LDAP_NAME_ATTRIBUTE": self.LDAP_NAME_ATTRIBUTE,
        }
        not_none = None not in required.values()
        if not not_none and not description:
            missing_values = [key for (key, value) in required.items() if value is None]
            description = f"Missing required values for {missing_values}"

        return FeatureDetails(
            enabled=self.LDAP_AUTH_ENABLED and not_none,
            description=description,
        )

    @property
    def LDAP_ENABLED(self) -> bool:
        """Indicates if LDAP authentication is configured and enabled."""
        return self.LDAP_FEATURE.enabled

    # ===============================================
    # OIDC Configuration
    OIDC_AUTH_ENABLED: bool = False
    """Flag to enable OpenID Connect (OIDC) authentication."""
    OIDC_CLIENT_ID: str | None = None
    """OIDC client ID."""
    OIDC_CLIENT_SECRET: MaskedNoneString = None
    """OIDC client secret (masked)."""
    OIDC_CONFIGURATION_URL: str | None = None
    """URL to the OIDC provider's configuration discovery document."""
    OIDC_SIGNUP_ENABLED: bool = True
    """Flag to allow new user sign-ups via OIDC."""
    OIDC_USER_GROUP: str | None = None
    """OIDC group claim value required for regular user access."""
    OIDC_ADMIN_GROUP: str | None = None
    """OIDC group claim value required for admin access."""
    OIDC_AUTO_REDIRECT: bool = False
    """Flag to automatically redirect to OIDC provider for login."""
    OIDC_PROVIDER_NAME: str = "OAuth"
    """Display name for the OIDC provider on the login page."""
    OIDC_REMEMBER_ME: bool = False
    """Flag to enable "remember me" functionality for OIDC logins."""
    OIDC_USER_CLAIM: str = "email"
    """The OIDC claim to use as the primary user identifier (e.g., 'email', 'sub')."""
    OIDC_NAME_CLAIM: str = "name"
    """The OIDC claim to use for the user's full name."""
    OIDC_GROUPS_CLAIM: str | None = "groups"
    """The OIDC claim containing the user's group memberships."""
    OIDC_SCOPES_OVERRIDE: str | None = None
    """Optional override for OIDC scopes (comma-separated)."""
    OIDC_TLS_CACERTFILE: str | None = None
    """Path to a CA certificate file for OIDC provider TLS validation."""

    @property
    def OIDC_REQUIRES_GROUP_CLAIM(self) -> bool:
        """Indicates if OIDC authentication requires group claim validation."""
        return self.OIDC_USER_GROUP is not None or self.OIDC_ADMIN_GROUP is not None

    @property
    def OIDC_FEATURE(self) -> FeatureDetails:
        """Details about the OIDC feature status, including validation."""
        description = None if self.OIDC_AUTH_ENABLED else "OIDC_AUTH_ENABLED is false"
        required = {
            "OIDC_CLIENT_ID": self.OIDC_CLIENT_ID,
            "OIDC_CLIENT_SECRET": self.OIDC_CLIENT_SECRET,
            "OIDC_CONFIGURATION_URL": self.OIDC_CONFIGURATION_URL,
            "OIDC_USER_CLAIM": self.OIDC_USER_CLAIM,
        }
        not_none = None not in required.values()
        if not not_none and not description:
            missing_values = [key for (key, value) in required.items() if value is None]
            description = f"Missing required values for {missing_values}"

        valid_group_claim = True
        if self.OIDC_REQUIRES_GROUP_CLAIM and self.OIDC_GROUPS_CLAIM is None:
            if not description:
                description = "OIDC_GROUPS_CLAIM is required when OIDC_USER_GROUP or OIDC_ADMIN_GROUP are provided"
            valid_group_claim = False

        return FeatureDetails(
            enabled=self.OIDC_AUTH_ENABLED and not_none and valid_group_claim,
            description=description,
        )

    @property
    def OIDC_READY(self) -> bool:
        """Indicates if OIDC authentication is configured and ready to use."""
        return self.OIDC_FEATURE.enabled

    # ===============================================
    # OpenAI Configuration

    OPENAI_BASE_URL: str | None = None
    """The base URL for the OpenAI API. Leave this unset for most use cases."""
    OPENAI_API_KEY: MaskedNoneString = None
    """Your OpenAI API key. Required to enable OpenAI features (masked)."""
    OPENAI_MODEL: str = "gpt-4o"
    """Which OpenAI model to send requests to. Leave this unset for most use cases."""
    OPENAI_CUSTOM_HEADERS: dict[str, str] = {}
    """Custom HTTP headers to send with each OpenAI request."""
    OPENAI_CUSTOM_PARAMS: dict[str, Any] = {}
    """Custom HTTP parameters to send with each OpenAI request."""
    OPENAI_ENABLE_IMAGE_SERVICES: bool = True
    """Whether to enable image-related features in OpenAI."""
    OPENAI_WORKERS: int = 2
    """
    Number of OpenAI workers per request. Higher values may increase
    processing speed but will incur additional API costs.
    """
    OPENAI_SEND_DATABASE_DATA: bool = True
    """
    Sending database data may increase accuracy in certain requests
    but will incur additional API costs.
    """
    OPENAI_REQUEST_TIMEOUT: int = 60
    """
    The number of seconds to wait for an OpenAI request to complete before cancelling.
    """

    @property
    def OPENAI_FEATURE(self) -> FeatureDetails:
        """Details about the OpenAI feature status, including validation."""
        description = None
        if not self.OPENAI_API_KEY:
            description = "OPENAI_API_KEY is not set"
        elif not self.OPENAI_MODEL:  # Corrected: check if OPENAI_MODEL is not set
            description = "OPENAI_MODEL is not set"

        return FeatureDetails(
            enabled=bool(self.OPENAI_API_KEY and self.OPENAI_MODEL),
            description=description,
        )

    @property
    def OPENAI_ENABLED(self) -> bool:
        """Indicates if OpenAI integration is configured and enabled."""
        return self.OPENAI_FEATURE.enabled

    # ===============================================
    # TLS

    TLS_CERTIFICATE_PATH: str | os.PathLike[str] | None = None
    """Path where the TLS certificate resides."""

    TLS_PRIVATE_KEY_PATH: str | os.PathLike[str] | None = None
    """Path where the TLS private key resides."""


class PluginSettings(BaseSettings):
    """
    Base settings class for Marvin plugins.

    Plugins can inherit from this class to define their own specific settings,
    which will be loaded with a prefix based on the plugin's name.
    """

    # Plugin Name
    PLUGIN_NAME: str
    """The name of the plugin."""

    # Plugin Version
    PLUGIN_VERSION: str
    """The version of the plugin."""

    # Plugin Description
    PLUGIN_DESCRIPTION: str | None = None
    """An optional description of the plugin."""

    # Plugin Author
    PLUGIN_AUTHOR: str | None = None
    """The author of the plugin."""

    # Plugin Author Email
    PLUGIN_AUTHOR_EMAIL: str | None = None
    """The email address of the plugin author."""

    model_config = SettingsConfigDict(arbitrary_types_allowed=True, extra="allow")


def app_settings_constructor(
    data_dir: Path,
    production: bool,
    env_file: Path,
    env_secrets: Path,
    secrets_dir: Path,
    env_encoding: str = "utf-8",
) -> AppSettings:
    """
    Factory function to create and configure the main `AppSettings` object.

    This function handles the initialization of settings, including loading
    from .env files, determining the secret key, and configuring the database
    provider.

    Args:
        data_dir (Path): The application's data directory.
        production (bool): Flag indicating if in production mode.
        env_file (Path): Path to the main .env file.
        env_secrets (Path): Path to the .env.secrets file.
        secrets_dir (Path): Directory for storing secrets.
        env_encoding (str): Encoding for .env files.

    Returns:
        AppSettings: The configured application settings object.
    """

    app_settings = AppSettings(
        _env_file=env_file,  # type: ignore # pydantic-settings internal
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
    env_encoding: str = "utf-8",
    description: str | None = None,
    author: str | None = None,
    author_email: str | None = None,
    env_nested_delimiter: str = "__",
    settings_class: type[PluginSettings] = PluginSettings,  # Changed default to PluginSettings
) -> PluginSettings:
    """
    Factory function to create and configure `PluginSettings` objects.

    This function handles the initialization of plugin-specific settings,
    loading from .env files with a plugin-specific prefix.

    Args:
        name (str): The name of the plugin.
        version (str): The version of the plugin.
        env_file (Path): Path to the main .env file.
        data_dir (Path): The application's data directory.
        production (bool): Flag indicating if in production mode.
        env_secrets (Path): Path to the .env.secrets file.
        secrets_dir (Path): Directory for storing secrets.
        env_encoding (str): Encoding for .env files.
        description (str | None): Optional description of the plugin.
        author (str | None): Optional author of the plugin.
        author_email (str | None): Optional author email of the plugin.
        env_nested_delimiter (str): Delimiter for nested environment variables.
        settings_class (type[PluginSettings]): The specific PluginSettings subclass
                                               to instantiate. Defaults to `PluginSettings`.

    Returns:
        PluginSettings: The configured plugin settings object.
    """
    app_settings = settings_class(
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
