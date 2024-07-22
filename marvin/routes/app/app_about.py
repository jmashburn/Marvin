from fastapi import APIRouter

from marvin.core.config import get_app_settings

router = APIRouter(prefix="/about")


@router.get("")
def get_app_info():
    return {"message": "Hello World {APP_VERSION}"}


@router.get("/startup-info")
def get_startup_info():
    settings = get_app_settings()
    return settings
