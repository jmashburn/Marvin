from fastapi import APIRouter

from . import app_about, health

router = APIRouter()
router.include_router(app_about.router, tags=["App: About"])
router.include_router(health.router, tags=["App: Health Check"])
