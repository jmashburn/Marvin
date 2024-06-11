from fastapi import APIRouter

from . import marvin

router = APIRouter(prefix="/api")
router.include_router(marvin.router)

# Addons
