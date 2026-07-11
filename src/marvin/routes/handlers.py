"""
This module provides custom exception handlers for the FastAPI application
within Marvin.

It includes utilities for logging validation errors in a structured format
and for registering these handlers with the FastAPI application, typically
during development or testing phases for enhanced debugging.
"""

from collections.abc import Callable  # For type hinting the handler function signature

from fastapi import FastAPI, Request, status  # Core FastAPI components
from fastapi.exceptions import ResponseValidationError  # Specific exception to handle
from fastapi.responses import JSONResponse  # For crafting custom JSON error responses
from sqlalchemy.exc import IntegrityError  # Database integrity errors

from marvin.core.config import get_app_settings  # Access application settings
from marvin.core.exceptions import (  # Core application exceptions
    MissingClaimException,
    NoEntryFound,
    PermissionDenied,
    RateLimitError,
    SlugError,
    UserLockedOut,
    VideoDownloadError,
)
from marvin.core.root_logger import get_logger  # Application logger

# Initialize logger for this module
logger = get_logger()


def log_wrapper(request: Request, exc: Exception) -> None:  # Changed `e` to `exc` for clarity
    """
    Logs details of an exception in a structured format.

    This wrapper formats log messages to clearly delineate the start and end
    of the error report, including the request method, URL, and the exception itself.
    It is typically used within exception handlers.

    Args:
        request (Request): The FastAPI Request object associated with the error.
        exc (Exception): The exception that was raised.
    """
    logger.error(" Start 422 Unprocessable Entity Error ".center(80, "-"))  # Standardized separator
    logger.error(f"Request: {request.method} {request.url}")
    logger.error(f"Error Details: {exc}")
    # If `exc.errors()` is available (as in RequestValidationError), it could be logged too for more detail.
    # For ResponseValidationError, `exc.body` might contain the problematic response data.
    if isinstance(exc, ResponseValidationError) and hasattr(exc, "body"):
        logger.error(f"Problematic Response Body: {exc.body}")  # Log the body causing response validation error
    logger.error(" End 422 Unprocessable Entity Error ".center(80, "-"))


def register_debug_handler(app: FastAPI) -> Callable | None:
    """
    Registers a custom exception handler for `ResponseValidationError` with the FastAPI app.

    This handler is intended for use in non-production environments (i.e., not PRODUCTION
    or when TESTING is True) to provide more detailed validation error responses from
    outgoing data (responses). It logs the error and returns a JSON response with
    a 422 status code.

    If in production and not testing, this function does nothing.

    Args:
        app (FastAPI): The FastAPI application instance.

    Returns:
        Callable | None: The exception handler function if registered, otherwise None.
    """
    settings = get_app_settings()

    # Only register this debug handler if not in production, or if explicitly testing
    if settings.PRODUCTION and not settings.TESTING:
        logger.info("ResponseValidationError debug handler not registered in production environment (unless TESTING is True).")
        return None

    @app.exception_handler(ResponseValidationError)
    async def validation_exception_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
        """
        Custom exception handler for `ResponseValidationError`.

        This type of error occurs when the data being sent in a response
        fails Pydantic validation against the `response_model`. This handler
        logs the error details and returns a standardized JSON error response
        with HTTP status code 422.

        Args:
            request (Request): The FastAPI Request object.
            exc (ResponseValidationError): The `ResponseValidationError` instance.

        Returns:
            JSONResponse: A JSON response detailing the validation error.
        """
        # Log the detailed error using the wrapper
        log_wrapper(request, exc)

        # Format a user-friendly message from the exception
        # `exc.errors()` provides detailed error information for Pydantic models
        error_details = exc.errors() if hasattr(exc, "errors") else str(exc)

        content = {
            "detail": {
                "message": "Response validation failed. There was an issue with the data sent from the server.",
                "errors": error_details,
            }
        }
        # Return a JSON response with status code 422
        return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    logger.info("Registered custom ResponseValidationError debug handler.")
    return validation_exception_handler


def register_core_exception_handlers(app: FastAPI) -> None:
    """
    Registers global exception handlers for core Marvin exceptions.

    These handlers convert application-specific exceptions into appropriate HTTP responses,
    enabling consistent error handling across all routes without requiring HTTPException.

    Registered exceptions:
    - PermissionDenied: Returns 403 Forbidden when user lacks access rights
    - NoEntryFound: Returns 404 Not Found when a requested resource doesn't exist
    - SlugError: Returns 409 Conflict when a slug collision occurs
    - RateLimitError: Returns 429 Too Many Requests when rate limit is exceeded
    - UserLockedOut: Returns 423 Locked when user account is locked
    - MissingClaimException: Returns 401 Unauthorized when required auth claim is missing
    - VideoDownloadError: Returns 500 Internal Server Error for video download failures
    - IntegrityError: Returns 409 Conflict for database integrity violations

    Usage in routes:
        Instead of: raise HTTPException(status_code=404, detail="Not found")
        Use:        raise NoEntryFound("Resource not found")

    Args:
        app (FastAPI): The FastAPI application instance.
    """

    @app.exception_handler(PermissionDenied)
    async def permission_denied_handler(request: Request, exc: PermissionDenied) -> JSONResponse:
        """Handle PermissionDenied: user lacks required permissions."""
        logger.warning(f"PermissionDenied: {request.method} {request.url.path} - {exc}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc) or "You do not have permission to perform this action"},
        )

    @app.exception_handler(NoEntryFound)
    async def no_entry_found_handler(request: Request, exc: NoEntryFound) -> JSONResponse:
        """Handle NoEntryFound: requested resource doesn't exist."""
        logger.info(f"NoEntryFound: {request.method} {request.url.path} - {exc}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc) or "The requested resource was not found"},
        )

    @app.exception_handler(SlugError)
    async def slug_error_handler(request: Request, exc: SlugError) -> JSONResponse:
        """Handle SlugError: slug already exists (conflict)."""
        logger.warning(f"SlugError: {request.method} {request.url.path} - {exc}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc) or "A resource with this slug already exists"},
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_error_handler(request: Request, exc: RateLimitError) -> JSONResponse:
        """Handle RateLimitError: too many requests."""
        logger.warning(f"RateLimitError: {request.method} {request.url.path} - {exc}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": str(exc) or "Rate limit exceeded. Please try again later"},
        )

    @app.exception_handler(UserLockedOut)
    async def user_locked_out_handler(request: Request, exc: UserLockedOut) -> JSONResponse:
        """Handle UserLockedOut: user account is locked."""
        logger.warning(f"UserLockedOut: {request.method} {request.url.path} - {exc}")
        return JSONResponse(
            status_code=status.HTTP_423_LOCKED,
            content={"detail": str(exc) or "User account is locked"},
        )

    @app.exception_handler(MissingClaimException)
    async def missing_claim_handler(request: Request, exc: MissingClaimException) -> JSONResponse:
        """Handle MissingClaimException: required authentication claim is missing."""
        logger.warning(f"MissingClaimException: {request.method} {request.url.path} - {exc}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc) or "Required authentication claim is missing"},
        )

    @app.exception_handler(VideoDownloadError)
    async def video_download_error_handler(request: Request, exc: VideoDownloadError) -> JSONResponse:
        """Handle VideoDownloadError: video download failed."""
        logger.error(f"VideoDownloadError: {request.method} {request.url.path} - {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc) or "Failed to download video"},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        """Handle IntegrityError: database integrity constraint violation."""
        logger.error(f"IntegrityError: {request.method} {request.url.path} - {exc}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "A database constraint was violated. This resource may already exist or references invalid data."},
        )

    logger.info(
        "Registered global core exception handlers (PermissionDenied, NoEntryFound, SlugError, RateLimitError, UserLockedOut, MissingClaimException, VideoDownloadError, IntegrityError)"
    )
