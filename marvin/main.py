"""
This module serves as an alternative entry point for the Marvin FastAPI application,
specifically configured for deployment as an AWS Lambda function using Mangum.

It mirrors much of the setup in `marvin.app.py`, including FastAPI app initialization,
middleware configuration, lifespan events (database initialization), and route registration.
However, it notably excludes the Uvicorn `main()` function and the scheduler setup,
as those are typically not managed within the Lambda execution model in the same way.

The `Mangum` adapter is used to wrap the FastAPI application, making it compatible
with AWS Lambda's event and context invocation model.
"""

from collections.abc import AsyncGenerator  # For async generator type hint
from contextlib import asynccontextmanager  # For creating async context managers (lifespan)

from fastapi import FastAPI  # The main FastAPI class
from fastapi.middleware.cors import CORSMiddleware  # Middleware for CORS
from fastapi.middleware.gzip import GZipMiddleware  # Middleware for GZip compression
from mangum import Mangum  # ASGI adapter for AWS Lambda

# Marvin core components
from marvin.core.config import get_app_settings  # Access application settings
from marvin.core.root_logger import get_logger  # Application logger
from marvin.core.settings.static import APP_VERSION  # Static application version
from marvin.routes import router as main_api_router  # Main API router
from marvin.routes.handlers import register_debug_handler  # Custom exception handlers

# Initialize global settings and logger instances
settings = get_app_settings()
logger = get_logger()

# Application description for OpenAPI documentation
# Uses f-string to embed the current application version. Bolding for emphasis.
description = f"""
    Marvin API - Your central hub for managing things.
    Version: <b>{APP_VERSION}</b>
"""


@asynccontextmanager
async def lifespan_fn(_app: FastAPI) -> AsyncGenerator[None, None]:  # Renamed app to _app
    """
    Asynchronous context manager for FastAPI application lifespan events (AWS Lambda context).

    This function handles tasks that need to occur at application startup
    (before `yield`) and shutdown (after `yield`) when deployed on AWS Lambda.

    Startup tasks include:
    - Logging system startup.
    - Initializing the database (running migrations, creating default data via `init_db.main()`).
    - Logging application settings (excluding sensitive information).

    NOTE: Unlike `marvin.app.py`, this lifespan function does NOT start the scheduler service,
    as scheduled tasks are typically handled differently in serverless environments (e.g.,
    using AWS EventBridge or scheduled Lambda functions).

    Args:
        _app (FastAPI): The FastAPI application instance (passed by FastAPI).

    Yields:
        None: Control back to FastAPI after startup tasks are complete.
    """
    # --- Lambda Cold Start / Container Initialization ---
    logger.info("------ LAMBDA/SYSTEM STARTUP INITIATED ------")

    logger.info("Starting: Database initialization...")
    import marvin.db.init_db as init_db  # Local import

    try:
        init_db.main()  # Run database migrations and initial data seeding
        logger.info("Completed: Database initialization.")
    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
        # In a Lambda, failing DB init might be critical. Consider how to handle.

    logger.info("------ APPLICATION SETTINGS (Non-Sensitive) on Lambda------")
    # Log application settings, excluding sensitive fields
    loggable_settings = settings.model_dump_json(
        indent=2,
        exclude={"SECRET", "ENV_SECRETS", "theme"},  # Exclude sensitive or verbose fields
    )
    logger.info(loggable_settings)
    logger.info("------ LAMBDA/SYSTEM STARTUP COMPLETE ------")

    yield  # Application is ready to handle requests

    # --- Lambda Container Shutdown (less common to hook into explicitly) ---
    logger.info("------ LAMBDA/SYSTEM SHUTDOWN (Placeholder) ------")
    # Cleanup tasks specific to Lambda shutdown could go here, though Mangum handles much of the cycle.


# Initialize the FastAPI application instance
app = FastAPI(
    title="Marvin API (Lambda)",  # Title for OpenAPI documentation, noting Lambda context
    description=description,
    version=APP_VERSION,
    docs_url=settings.DOCS_URL,  # Serve docs if configured (might be disabled for Lambda prod)
    redoc_url=settings.REDOC_URL,  # Serve ReDoc if configured
    lifespan=lifespan_fn,  # Register the lifespan context manager
    # For Lambda, root_path might be important if deployed under a stage in API Gateway
    # root_path=f"/{settings.AWS_STAGE}" if settings.AWS_STAGE else None, # Example
)

# Add GZip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses larger than 1KB

# Configure CORS middleware for non-production environments (or if needed for Lambda)
if not settings.PRODUCTION:
    allowed_origins = [
        "http://localhost:3000",  # For local development accessing a locally simulated Lambda
        # Add other origins as needed
    ]
    logger.info(f"CORS enabled for non-production Lambda. Allowed origins: {allowed_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production CORS settings for Lambda would typically be more restrictive
    # or handled at the API Gateway level.
    logger.info("CORS configuration for production Lambda would apply here if specified.")


# Register custom debug/error handlers
register_debug_handler(app)


def include_api_routers() -> None:  # Renamed from api_routers for clarity
    """
    Includes the main API router into the FastAPI application.
    """
    app.include_router(main_api_router)  # Use the main_api_router imported from marvin.routes
    logger.info("API routers included in Lambda app.")


# Include all API routes
include_api_routers()

# Handler for AWS Lambda, created by wrapping the FastAPI app with Mangum.
# This `handler` is what AWS Lambda will invoke.
handler = Mangum(app, lifespan="on")  # Ensure Mangum handles lifespan events correctly
logger.info("Mangum handler created for AWS Lambda.")

# Note: No `if __name__ == "__main__":` block with uvicorn.run(),
# as this file is intended for Lambda deployment, not direct execution with Uvicorn.
