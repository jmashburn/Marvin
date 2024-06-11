from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from marvin.core.config import get_app_settings
from marvin.core.root_logger import get_logger
from marvin.core.settings.static import APP_VERSION
from marvin.routes import router
from marvin.routes.handlers import register_debug_handler


settings = get_app_settings()

logger = get_logger()

description = f"""
    **{APP_VERSION}**
"""


@asynccontextmanager
async def lifespan_fn(_: FastAPI) -> AsyncGenerator[None, None]:
    """
    lifespan_fn controls the startup and shutdown of the FastAPI Application
    This function is called when the FastAPI application starts and stops

    """
    logger.info("start: ")
    logger.info("end: ")

    logger.info("------SYSTEM STARTUP------")
    logger.info("------APP SETTINGS------")
    logger.info(
        settings.model_dump_json(
            indent=2,
            exclude={"SECRET", "ENV_SECRETS"},
        )
    )

    yield

    logger.info("------SYSTEM SHUTDOWN------")


app = FastAPI(
    title="Marvin",
    description=description,
    version=APP_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    lifespan=lifespan_fn,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

if not settings.PRODUCTION:
    allowed_origins = "http://localhost:3000"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

register_debug_handler(app)


def api_routers():
    app.include_router(router)


api_routers()


def main():
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True,
        reload_dirs=["marvin"],
        reload_delay=2,
        log_level="info",
        use_colors=True,
        log_config=None,
        workers=1,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
