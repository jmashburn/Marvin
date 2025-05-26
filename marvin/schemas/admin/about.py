"""
This module defines Pydantic schemas used for representing administrative "about"
information, application statistics, configuration status, and theme details
within the Marvin application.

These schemas are primarily used as response models for administrative endpoints.
"""

from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model for Marvin schemas


class AppStatistics(_MarvinModel):
    """
    Schema for basic application statistics.
    """

    total_users: int  # The total number of registered users in the system.
    total_groups: int  # The total number of groups in the system.


class AppInfo(_MarvinModel):
    """
    Schema for general application information.
    This model is often extended by more specific "about" info models.
    """

    production: bool  # Indicates if the application is running in production mode.
    version: str  # The current version of the application (e.g., "1.0.0", "develop").
    demo_status: bool  # Indicates if the application is running in demo mode.
    allow_signup: bool  # Indicates if new user signups are currently allowed.
    default_group_slug: str | None = None  # Slug of the default group for new users, if applicable.
    default_household_slug: str | None = None  # Legacy or alternative naming for default group slug.
    enable_oidc: bool  # Indicates if OpenID Connect (OIDC) authentication is enabled.
    oidc_redirect: bool  # Indicates if automatic redirect to OIDC provider is enabled.
    oidc_provider_name: str  # Display name of the configured OIDC provider.
    enable_openai: bool  # Indicates if OpenAI integration is enabled.
    enable_openai_image_services: bool  # Indicates if OpenAI image-related services are specifically enabled.


class AppTheme(_MarvinModel):
    """
    Schema defining the color palette for the application's light and dark themes.
    Provides default hex color values for various UI elements.
    """

    # Light Theme Colors
    light_primary: str = "#E58325"  # Primary color for light theme.
    light_accent: str = "#007A99"  # Accent color for light theme.
    light_secondary: str = "#973542"  # Secondary color for light theme.
    light_success: str = "#43A047"  # Success color (e.g., for positive feedback) for light theme.
    light_info: str = "#1976D2"  # Informational color for light theme.
    light_warning: str = "#FF6D00"  # Warning color for light theme.
    light_error: str = "#EF5350"  # Error color (e.g., for error messages) for light theme.

    # Dark Theme Colors (currently same as light, likely placeholders or to be customized)
    dark_primary: str = "#E58325"  # Primary color for dark theme.
    dark_accent: str = "#007A99"  # Accent color for dark theme.
    dark_secondary: str = "#973542"  # Secondary color for dark theme.
    dark_success: str = "#43A047"  # Success color for dark theme.
    dark_info: str = "#1976D2"  # Informational color for dark theme.
    dark_warning: str = "#FF6D00"  # Warning color for dark theme.
    dark_error: str = "#EF5350"  # Error color for dark theme.


class AppStartupInfo(_MarvinModel):
    """
    Schema for information relevant to the application's startup state,
    particularly concerning initial setup or first login.
    """

    is_first_login: bool
    """
    Indicates the application's best guess that this might be the first time
    any user (or specifically an admin) is logging in. Currently, its logic
    relies on the presence of the default 'changeme@example.com' admin user.
    Once that default user's email is changed or the user is removed, this flag
    will consistently return False.
    """
    is_demo: bool  # Indicates if the application is currently running in demo mode.


class AdminAboutInfo(AppInfo):
    """
    Schema for detailed application information, extending `AppInfo` with
    additional details relevant for administrators.
    """

    versionLatest: str  # The latest available version of the application (e.g., fetched from GitHub).
    api_port: int  # The port on which the API is running.
    api_docs: bool  # Indicates if API documentation (e.g., Swagger UI) is enabled.
    db_type: str  # The type of database being used (e.g., "sqlite", "postgres").
    db_url: str | None = None  # The database connection URL (potentially masked for security).
    default_group: str  # The name of the default group for new users.
    build_id: str  # The Git commit hash or build identifier for the current application build.


class CheckAppConfig(_MarvinModel):
    """
    Schema representing the status of various critical application configurations.
    Used to quickly assess if key features are configured and ready for use.
    """

    email_ready: bool  # True if SMTP email settings are configured and enabled.
    ldap_ready: bool  # True if LDAP authentication settings are configured and enabled.
    oidc_ready: bool  # True if OIDC authentication settings are configured and enabled.
    enable_openai: bool  # True if OpenAI integration is configured and enabled.
    base_url_set: bool  # True if the application's BASE_URL has been changed from its default value.
    is_up_to_date: bool  # True if the current application version is the latest available, or if it's a development build.
