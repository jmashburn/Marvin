from fastapi import APIRouter, Depends, Response

from marvin.core.config import get_app_settings
from marvin.core.settings.static import APP_VERSION
from marvin.routes._base import UserAPIRouter
from marvin.schemas.app import AppInfo, AppStartupInfo, AppTheme

router = UserAPIRouter(prefix="/about")


@router.get("", response_model=AppInfo)
def get_app_info():
    settings = get_app_settings()

    return AppInfo(
        version=APP_VERSION,
        production=settings.PRODUCTION,
    )


@router.get("/startup-info", response_model=AppStartupInfo)
def get_startup_info():
    settings = get_app_settings()

    return AppStartupInfo()


@router.get("/theme", response_model=AppTheme)
def get_app_theme(resp: Response):
    settings = get_app_settings()

    resp.header["Cache-Control"] = "public, max-age=604600"
    return AppTheme(**settings.theme.model_dump())
