from fastapi import APIRouter

from . import providers_controller

router = APIRouter()
router.include_router(providers_controller.router, tags=["AI: Providers"])
