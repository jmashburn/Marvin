from fastapi import APIRouter, Depends, Response

from marvin.core.config import get_app_settings
from marvin.core.settings.static import APP_VERSION

router = APIRouter(prefix="/about")


@router.get("")
def get_app_info():
    return {"message": "Hello World {APP_VERSION}"}


@router.get("/startup-info")
def get_startup_info():
    settings = get_app_settings()
    return settings
