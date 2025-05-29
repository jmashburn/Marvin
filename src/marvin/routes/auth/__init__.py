from fastapi import APIRouter

from . import auth_controller

router = APIRouter(prefix="/auth")
router.include_router(auth_controller.public_router)
router.include_router(auth_controller.user_router)
