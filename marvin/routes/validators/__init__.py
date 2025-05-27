from fastapi import APIRouter

from . import validator_controller

prefix = "/validators"

router = APIRouter()

router.include_router(validator_controller.router, prefix=prefix, tags=["Validators"], include_in_schema=False)
