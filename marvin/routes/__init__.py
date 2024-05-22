from fastapi import APIRouter

from . import app

router = APIRouter(prefix="/api")

router.include_router(app.router)
