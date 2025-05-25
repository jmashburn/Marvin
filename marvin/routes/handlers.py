"""
This module provides custom exception handlers for the FastAPI application
within Marvin.

It includes utilities for logging validation errors in a structured format
and for registering these handlers with the FastAPI application, typically
during development or testing phases for enhanced debugging.
"""
from fastapi import FastAPI, Request, status # Core FastAPI components
from fastapi.exceptions import ResponseValidationError # Specific exception to handle
from fastapi.responses import JSONResponse # For crafting custom JSON error responses

from marvin.core.config import get_app_settings # Access application settings
from marvin.core.root_logger import get_logger # Application logger

# Initialize logger for this module
logger = get_logger()


def log_wrapper(request: Request, exc: Exception) -> None: # Changed `e` to `exc` for clarity
    """
    Logs details of an exception in a structured format.

    This wrapper formats log messages to clearly delineate the start and end
    of the error report, including the request method, URL, and the exception itself.
    It is typically used within exception handlers.

    Args:
        request (Request): The FastAPI Request object associated with the error.
        exc (Exception): The exception that was raised.
    """
    logger.error(" Start 422 Unprocessable Entity Error ".center(80, "-")) # Standardized separator
    logger.error(f"Request: {request.method} {request.url}")
    logger.error(f"Error Details: {exc}")
    # If `exc.errors()` is available (as in RequestValidationError), it could be logged too for more detail.
    # For ResponseValidationError, `exc.body` might contain the problematic response data.
    if isinstance(exc, ResponseValidationError) and hasattr(exc, 'body'):
        logger.error(f"Problematic Response Body: {exc.body}") # Log the body causing response validation error
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
        error_details = exc.errors() if hasattr(exc, 'errors') else str(exc)
        
        content = {
            "detail": {
                "message": "Response validation failed. There was an issue with the data sent from the server.",
                "errors": error_details,
            }
        }
        # Return a JSON response with status code 422
        return JSONResponse(
            content=content, 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    logger.info("Registered custom ResponseValidationError debug handler.")
    return validation_exception_handler
