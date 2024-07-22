from fastapi import APIRouter
from . import test

prefix = "/v2"

router = APIRouter(prefix=prefix)
router.included_router(test.router)
