from fastapi import FastAPI, Request, status
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse

from marvin.core.config import get_app_settings
from marvin.core.root_logger import get_logger

logger = get_logger()


def log_wrapper(request: Request, e):
    logger.error("Start 422 Error".center(60, "-"))
    logger.error(f"{request.method} {request.url}")
    logger.error(f"error is {e}")
    logger.error("End 422 Error".center(60, "-"))


def register_debug_handler(app: FastAPI):
    settings = get_app_settings()

    if settings.PRODUCTION and not settings.TESTING:
        return

    @app.exception_handler(ResponseValidationError)
    async def validation_exception_handler(request: Request, exc: ResponseValidationError):
        exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
        log_wrapper(request, exc)
        content = {"status _code": status.HTTP_422_UNPROCESSABLE_ENTITY, "message": exc_str, "data": None}
        return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    return validation_exception_handler
