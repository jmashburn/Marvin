from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from mangum import Mangum


from marvin.core.config import get_app_settings
from marvin.core.root_logger import get_logger
from marvin.core.settings.static import APP_VERSION
from marvin.routes import router
from marvin.routes.handlers import register_debug_handler


settings = get_app_settings()

logger = get_logger()

description = f"""
    <b>{APP_VERSION}</b>
"""


@asynccontextmanager
async def lifespan_fn(_: FastAPI) -> AsyncGenerator[None, None]:
    """
    lifespan_fn controls the startup and shutdown of the FastAPI Application
    This function is called when the FastAPI application starts and stops

    """
    logger.info("------SYSTEM STARTUP------")

    logger.info("start: database initialization")

    import marvin.db.init_db as init_db

    init_db.main()
    logger.info("end: database initialization")

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

# Handler for AWS Lambda
handler = Mangum(app)
