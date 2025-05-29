"""
This module serves as the main entry point for the Marvin FastAPI application.

It initializes the FastAPI application instance, configures middleware (CORS, GZip),
sets up lifespan events for application startup and shutdown (including database
initialization and scheduler startup), registers API routes, and provides a `main`
function to run the application using Uvicorn, primarily for development purposes.
"""

from collections.abc import AsyncGenerator  # For async generator type hint
from contextlib import asynccontextmanager  # For creating async context managers (lifespan)

import uvicorn  # ASGI server for running FastAPI
from fastapi import FastAPI  # The main FastAPI class
from fastapi.middleware.cors import CORSMiddleware  # Middleware for CORS
from fastapi.middleware.gzip import GZipMiddleware  # Middleware for GZip compression

# Marvin core components
from marvin.core.config import get_app_settings  # Access application settings
from marvin.core.root_logger import get_logger  # Application logger
from marvin.core.settings.static import APP_VERSION  # Static application version
from marvin.routes import router as main_api_router  # Main API router combining all app routes
from marvin.routes.handlers import register_debug_handler  # Registers custom exception handlers

# Scheduler components
from marvin.services.scheduler import SchedulerRegistry, SchedulerService
from marvin.services.scheduler import tasks as scheduler_tasks

# Initialize global settings and logger instances
settings = get_app_settings()
logger = get_logger()

# Application description for OpenAPI documentation
# Uses f-string to embed the current application version.
description = f"""
Marvin API - Your central hub for managing things.
Version: **{APP_VERSION}**
"""


@asynccontextmanager
async def lifespan_fn(_app: FastAPI) -> AsyncGenerator[None, None]:  # Renamed app to _app
    """
    Asynchronous context manager for FastAPI application lifespan events.

    This function handles tasks that need to occur at application startup
    (before `yield`) and shutdown (after `yield`).

    Startup tasks include:
    - Logging system startup.
    - Initializing the database (running migrations, creating default data via `init_db.main()`).
    - Starting the scheduler service (`start_scheduler()`).
    - Logging application settings (excluding sensitive information).

    Shutdown tasks include:
    - Logging system shutdown.

    Args:
        _app (FastAPI): The FastAPI application instance (passed by FastAPI, often unused in the function body).

    Yields:
        None: Control back to FastAPI after startup tasks are complete.
    """
    # --- Startup ---
    logger.info("------ SYSTEM STARTUP INITIATED ------")

    logger.info("Starting: Database initialization...")
    import marvin.db.init_db as init_db  # Local import to avoid premature DB calls if app is imported elsewhere

    try:
        init_db.main()  # Run database migrations and initial data seeding
        logger.info("Completed: Database initialization.")
    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
        # Depending on severity, might want to raise or exit here.

    logger.info("Starting: Scheduler service...")
    try:
        await start_scheduler()  # Register and start scheduled tasks
        logger.info("Completed: Scheduler service started.")
    except Exception as e:
        logger.exception(f"Scheduler service failed to start: {e}")

    logger.info("------ APPLICATION SETTINGS (Non-Sensitive) ------")
    # Log application settings, excluding potentially sensitive fields
    # Pydantic v2 uses model_dump_json
    loggable_settings = settings.model_dump_json(
        indent=2,
        exclude={"theme", "SECRET", "ENV_SECRETS"},  # Exclude sensitive or verbose fields
    )
    logger.info(loggable_settings)
    logger.info("------ SYSTEM STARTUP COMPLETE ------")

    yield  # Application runs after this point

    # --- Shutdown ---
    logger.info("------ SYSTEM SHUTDOWN INITIATED ------")
    # Add any cleanup tasks here (e.g., closing connections, flushing buffers)
    # For example:
    # if hasattr(some_service, 'shutdown'):
    #     await some_service.shutdown()
    logger.info("------ SYSTEM SHUTDOWN COMPLETE ------")


# Initialize the FastAPI application instance
app = FastAPI(
    title="Marvin API",  # Title for OpenAPI documentation
    description=description,  # Description from above
    version=APP_VERSION,  # Application version
    docs_url=settings.DOCS_URL,  # URL for Swagger UI (None if disabled in settings)
    redoc_url=settings.REDOC_URL,  # URL for ReDoc (None if disabled in settings)
    lifespan=lifespan_fn,  # Register the lifespan context manager
)

# Add GZip middleware to compress responses for supported clients
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses larger than 1KB

# Configure CORS (Cross-Origin Resource Sharing) middleware for non-production environments
if not settings.PRODUCTION:
    # Define allowed origins for CORS (typically frontend development server)
    allowed_origins = [
        "http://localhost:3000",  # Example: React frontend
        "http://localhost:8080",  # If API is also served/tested on a different port locally
    ]
    logger.info(f"CORS enabled for development. Allowed origins: {allowed_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # List of allowed origins
        allow_credentials=True,  # Allow cookies to be included in cross-origin requests
        allow_methods=["*"],  # Allow all standard HTTP methods
        allow_headers=["*"],  # Allow all headers
    )
else:
    logger.info("CORS middleware not enabled in production environment (or using different production CORS config).")


async def start_scheduler() -> None:
    """
    Registers scheduled tasks with the `SchedulerRegistry` and starts the `SchedulerService`.

    This function defines which tasks run at daily, minutely, and hourly intervals.
    Commented-out tasks indicate potential future or optional scheduled jobs.
    """
    logger.info("Registering scheduled tasks...")
    # Register daily tasks
    SchedulerRegistry.register_daily(
        # scheduler_tasks.purge_expired_tokens,
        # scheduler_tasks.purge_group_registration,
        # scheduler_tasks.purge_password_reset_tokens,
        # scheduler_tasks.purge_group_data_exports,
        # scheduler_tasks.create_mealplan_timeline_events,
        # scheduler_tasks.delete_old_checked_list_items,
    )

    # Register minutely tasks (currently ping and post_group_webhooks)
    SchedulerRegistry.register_minutely(scheduler_tasks.ping, scheduler_tasks.post_group_webhooks)

    # Register hourly tasks
    SchedulerRegistry.register_hourly(
        # scheduler_tasks.locked_user_reset,
    )

    # Print all registered jobs to the debug log for verification
    SchedulerRegistry.print_jobs()

    # Start the scheduler service (which will pick up registered tasks)
    await SchedulerService.start()


# Register custom debug/error handlers for the application
# This is conditional based on settings in register_debug_handler
register_debug_handler(app)


def include_api_routers() -> None:  # Renamed from api_routers for clarity
    """
    Includes the main API router into the FastAPI application.

    This function modularizes router inclusion. All application routes
    are aggregated under `main_api_router` (imported from `marvin.routes`).
    """
    app.include_router(main_api_router)  # Include all routes defined in marvin.routes
    logger.info("API routers included.")


# Include all API routes from marvin.routes package
include_api_routers()


def main() -> None:
    """
    Main function to run the Marvin FastAPI application using Uvicorn.

    This function is intended for development and local execution. It configures
    Uvicorn with settings for host, port, auto-reloading, logging, and workers.
    For production deployments, a more robust ASGI server setup (e.g., Uvicorn
    managed by Gunicorn or another process manager) is typically used.
    """
    logger.info(f"Starting Uvicorn server for Marvin app (Version: {APP_VERSION})...")
    # Configure and run Uvicorn server
    uvicorn.run(
        "marvin.app:app",  # Path to the FastAPI app instance (module:variable)
        host="0.0.0.0",  # Listen on all available network interfaces
        port=settings.API_PORT,  # Port from application settings
        reload=not settings.PRODUCTION,  # Enable auto-reloading in non-production environments
        reload_dirs=["."] if not settings.PRODUCTION else None,  # Directories to watch for changes
        reload_delay=2 if not settings.PRODUCTION else None,  # Delay before reloading
        log_level="info",  # Uvicorn's own log level
        use_colors=True,  # Enable colored logging output
        log_config=None,  # Use Uvicorn's default logging config (can be customized)
        workers=1,  # Number of worker processes (typically 1 for dev, more for prod)
        forwarded_allow_ips="*",  # Trust X-Forwarded-For headers from any IP (specific IPs better for prod)
    )


__all__ = ["main", "__version__"]

if __name__ == "__main__":
    # This block executes when the script is run directly (e.g., `python marvin/app.py`)
    main()
