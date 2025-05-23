from fastapi import APIRouter

from . import events_controller

router = APIRouter()

router.include_router(events_controller.router, tags=["Events: Options"])
