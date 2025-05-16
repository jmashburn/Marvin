from fastapi import Response, status

from marvin.core.config import get_app_settings
from marvin.core.settings.static import APP_VERSION
from pydantic import BaseModel
from marvin.routes._base import BasePublicController, BaseAPIRouter, controller


router = BaseAPIRouter(prefix="/health")


class HealthCheck(BaseModel):
    """Response model to validate and return when performing a health check."""

    status: str = "OK"


@controller(router)
class HealthController(BasePublicController):
    @router.get(
        "",
        summary="Perform a Health Check",
        response_description="Return HTTP Status Code 200 (OK)",
        status_code=status.HTTP_200_OK,
        response_model=HealthCheck,
    )
    def get_health(self, resp: Response):
        """
        ## Perform a Health Check
        Endpoint to perform a healthcheck on. This endpoint can primarily be used Docker
        to ensure a robust container orchestration and management is in place. Other
        services which rely on proper functioning of the API service will not deploy if this
        endpoint returns any other HTTP status code except 200 (OK).
        Returns:
            HealthCheck: Returns a JSON response with the health status
        """
        settings = get_app_settings()
        resp.headers["Cache-Control"] = "public, max-age=604600"
        return HealthCheck(status="OK")
