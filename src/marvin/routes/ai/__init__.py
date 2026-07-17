from fastapi import APIRouter

from . import operations_controller, providers_controller

router = APIRouter()
router.include_router(providers_controller.router, tags=["AI: Providers"])
router.include_router(operations_controller.router, tags=["AI: Operations"])
