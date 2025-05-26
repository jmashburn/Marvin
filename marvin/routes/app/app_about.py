"""
This module defines FastAPI routes for application-level "about" information
accessible to authenticated users within the Marvin application.

It provides endpoints to retrieve general application details (like version),
startup configuration information, and theme settings.
"""

from fastapi import Response  # APIRouter needed for router instantiation

from marvin.core.config import get_app_settings
from marvin.core.settings.static import APP_VERSION  # Current application version
from marvin.routes._base import UserAPIRouter  # Base router for authenticated user endpoints
from marvin.schemas.app import AppInfo, AppStartupInfo, AppTheme  # Pydantic response models

# APIRouter for "about" section, prefixed with /about and using UserAPIRouter for auth
# All routes in this controller will be under /app/about due to UserAPIRouter in main app and this prefix.
router = UserAPIRouter(prefix="/about")


@router.get("", response_model=AppInfo, summary="Get Basic Application Information")
def get_app_info() -> AppInfo:
    """
    Retrieves basic information about the application.

    This includes the application version and whether it's running in production mode.
    Accessible to any authenticated user.

    Returns:
        AppInfo: A Pydantic model containing the application version and production status.
    """
    settings = get_app_settings()  # Access application settings

    return AppInfo(
        version=APP_VERSION,  # From static settings
        production=settings.PRODUCTION,  # From dynamic settings
    )


@router.get("/startup-info", response_model=AppStartupInfo, summary="Get Application Startup Information")
def get_startup_info() -> AppStartupInfo:
    """
    Retrieves application startup information.

    NOTE: The `AppStartupInfo` schema is currently empty in the provided context.
    This endpoint will return an empty object unless `AppStartupInfo` is defined
    to include specific startup-related settings or data.
    Accessible to any authenticated user.

    Returns:
        AppStartupInfo: A Pydantic model (currently empty) intended for startup information.
    """
    # settings = get_app_settings()  # Access application settings (though not used in current AppStartupInfo)

    # Assuming AppStartupInfo might be populated with settings in the future.
    # For now, it will return an empty AppStartupInfo object if the schema has no fields.
    return AppStartupInfo()


@router.get("/theme", response_model=AppTheme, summary="Get Application Theme Settings")
def get_app_theme(resp: Response) -> AppTheme:
    """
    Retrieves the current application theme settings.

    The theme settings are fetched from the application configuration.
    This endpoint also sets cache control headers to allow client-side caching
    of the theme information for a specified duration.
    Accessible to any authenticated user.

    Args:
        resp (Response): The FastAPI Response object, used to set custom headers.

    Returns:
        AppTheme: A Pydantic model containing the application theme settings.
    """
    settings = get_app_settings()  # Access application settings

    # Set Cache-Control header to allow public caching for 1 week (604800 seconds)
    # max-age is in seconds. 604600 is slightly less than 7 days. Standard 7 days = 604800.
    resp.headers["Cache-Control"] = "public, max-age=604800"  # Corrected max-age

    # Return theme settings, unpacking the theme model from settings
    return AppTheme(**settings.theme.model_dump())
