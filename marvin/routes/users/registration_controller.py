from fastapi import APIRouter, Depends, HTTPException, status

from marvin.core.config import get_app_settings
from marvin.repos.all_repositories import get_repositories
from marvin.routes._base import BasePublicController, controller
from marvin.schemas.response import ErrorResponse
from marvin.schemas.user.registration import UserRegistrationCreate
from marvin.schemas.user.user import UserRead
from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import EventTypes, EventUserSignupData
from marvin.services.user.registration_service import RegistrationService

router = APIRouter(prefix="/register")


@controller(router)
class RegistrationController(BasePublicController):
    event_bus: EventBusService = Depends(EventBusService.as_dependency)

    @router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
    def register_new_user(self, data: UserRegistrationCreate):
        settings = get_app_settings()

        if not settings.ALLOW_SIGNUP and data.group_token is None or data.group_token == "":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse.respond("User Registration is Disabled"),
            )

        registration_service = RegistrationService(
            self.logger,
            get_repositories(self.session, group_id=None),
            self.translator,
        )

        result = registration_service.register_user(data)

        self.event_bus.dispatch(
            integration_id="registration",
            group_id=result.group_id,
            event_type=EventTypes.user_signup,
            document_data=EventUserSignupData(username=result.username, email=result.email),
        )

        return result
