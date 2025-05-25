"""
This module defines the health check endpoint for the Marvin application.

It provides a simple way to verify that the application is running and responsive.
This endpoint is typically used by monitoring services or container orchestration
platforms (like Kubernetes or Docker Swarm) to determine the application's health status.
"""
from fastapi import Response, status, APIRouter # Added APIRouter for router instantiation
from pydantic import BaseModel # For defining response models

# Marvin core components and base controller
from marvin.core.config import get_app_settings
# from marvin.core.settings.static import APP_VERSION # APP_VERSION import is unused in this file
from marvin.routes._base import BasePublicController, BaseAPIRouter, controller

# APIRouter for health check, using BaseAPIRouter for consistency.
# This is a public endpoint, so no specific authentication dependencies are added here.
# All routes will be under /app/health.
router = BaseAPIRouter(prefix="/health", tags=["Application - Health"])


class HealthCheck(BaseModel):
    """
    Response model for the health check endpoint.
    Indicates the operational status of the application.
    """
    status: str = "OK" # Default status indicating the application is healthy.


@controller(router)
class HealthController(BasePublicController):
    """
    Controller for the application health check endpoint.

    This controller provides a simple GET request handler that returns the
    health status of the application. It inherits from `BasePublicController`
    as health checks are typically public.
    """

    @router.get(
        "",
        summary="Perform a Health Check",
        response_description="Returns HTTP Status Code 200 (OK) if the application is healthy.",
        status_code=status.HTTP_200_OK, # Explicitly set success status code
        response_model=HealthCheck,    # Define the response model
    )
    def get_health(self, resp: Response) -> HealthCheck:
        """
        Performs a health check on the application.

        This endpoint is primarily used for automated health monitoring by services
        like Docker or Kubernetes. A successful response (HTTP 200 OK with
        `{"status": "OK"}`) indicates that the API service is operational.

        Cache-Control headers are set to allow public caching of this response,
        as its content is static and changes infrequently.

        Args:
            resp (Response): The FastAPI Response object, used to set custom headers.

        Returns:
            HealthCheck: A Pydantic model indicating the health status (typically "OK").
        """
        _ = get_app_settings() # Access settings, though not directly used in response here, ensures config loads.
        
        # Set Cache-Control header to allow public caching for 1 week (604800 seconds).
        # This can reduce load if the health check is called very frequently.
        # 604600 is slightly less than 7 days. Standard 7 days = 604800.
        resp.headers["Cache-Control"] = "public, max-age=604800" # Corrected max-age
        
        # Return the health status
        return HealthCheck(status="OK")
