"""
This module defines Pydantic schemas for application-level "about" information
within the Marvin application.

These schemas are typically used as response models for public or user-facing
endpoints that provide general details about the application, its version,
theme, and certain configuration statuses.

Note: Some model names in this file (e.g., `AppInfo`, `AppTheme`, `AdminAboutInfo`,
`CheckAppConfig`, `AppStatistics`) overlap with those in `marvin.schemas.admin.about`.
The definitions here might be intended for different contexts (e.g., less detailed
views for non-admin users) or could indicate a need for consolidation if they
serve identical purposes. This documentation reflects the models as defined in this specific file.
"""
from marvin.schemas._marvin import _MarvinModel # Base Pydantic model for Marvin schemas


class AppStatistics(_MarvinModel):
    """
    Schema for basic application statistics.
    
    NOTE: This model is currently defined without any fields (pass).
    It might be a placeholder for future implementation or defined elsewhere
    with actual fields (e.g., in `marvin.schemas.admin.about.AppStatistics`).
    """
    pass


class AppInfo(_MarvinModel):
    """
    Schema for general, publicly accessible application information.
    """
    production: bool # Indicates if the application is running in production mode.
    version: str # The current version of the application (e.g., "1.0.0", "develop").


class AppTheme(_MarvinModel):
    """
    Schema defining the color palette for the application's light and dark themes.
    Provides default hex color values for various UI elements, intended for client-side use.
    """
    # Light Theme Colors
    light_primary: str = "#E58325" # Primary color for light theme.
    light_accent: str = "#007A99"  # Accent color for light theme.
    light_secondary: str = "#973542" # Secondary color for light theme.
    light_success: str = "#43A047" # Success color for light theme.
    light_info: str = "#1976D2"    # Informational color for light theme.
    light_warning: str = "#FF6D00" # Warning color for light theme.
    light_error: str = "#EF5350"   # Error color for light theme.

    # Dark Theme Colors
    dark_primary: str = "#E58325"  # Primary color for dark theme.
    dark_accent: str = "#007A99"   # Accent color for dark theme.
    dark_secondary: str = "#973542" # Secondary color for dark theme.
    dark_success: str = "#43A047"  # Success color for dark theme.
    dark_info: str = "#1976D2"     # Informational color for dark theme.
    dark_warning: str = "#FF6D00"  # Warning color for dark theme.
    dark_error: str = "#EF5350"    # Error color for dark theme.


class AppStartupInfo(_MarvinModel):
    """
    Schema for information relevant to the application's startup state.

    NOTE: This model is currently defined as a placeholder (`...`).
    It might be intended for future use to convey specific startup details,
    or its definition might exist elsewhere (e.g., `marvin.schemas.admin.about.AppStartupInfo`
    has fields `is_first_login` and `is_demo`).
    """
    ... # Ellipsis indicates a placeholder, no fields defined here.


class AdminAboutInfo(AppInfo): # Note: This extends the AppInfo defined *in this file*.
    """
    Schema for detailed application information, extending the local `AppInfo`.
    This version is likely intended for administrative contexts, providing more
    details than the basic `AppInfo`.

    If `marvin.schemas.admin.about.AdminAboutInfo` is the canonical version,
    this might be a subset or an alternative definition.
    """
    versionLatest: str # The latest available version of the application.
    api_port: int # The port on which the API is running.
    api_docs: bool # Indicates if API documentation (e.g., Swagger UI) is enabled.
    db_type: str # The type of database being used (e.g., "sqlite", "postgres").
    db_url: str | None = None # The database connection URL (potentially masked).
    build_id: str # The Git commit hash or build identifier for the current build.
    # Note: This model lacks fields like `default_group` and OIDC/OpenAI flags
    # that are present in `marvin.schemas.admin.about.AdminAboutInfo`.


class CheckAppConfig(_MarvinModel):
    """
    Schema representing the status of various critical application configurations.
    This version is likely for user-facing checks or a subset of admin checks.

    If `marvin.schemas.admin.about.CheckAppConfig` is the canonical version,
    this might be a subset or an alternative definition.
    """
    email_ready: bool # True if SMTP email settings are configured and enabled.
    ldap_ready: bool # True if LDAP authentication settings are configured and enabled.
    oidc_ready: bool # True if OIDC authentication settings are configured and enabled.
    enable_openai: bool # True if OpenAI integration is configured and enabled.
    base_url_set: bool # True if the application's BASE_URL has been changed from its default.
    is_up_to_date: bool # True if the current application version is the latest or a dev build.
