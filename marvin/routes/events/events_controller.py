from functools import cached_property

from fastapi import APIRouter, Depends
from pydantic import UUID4

from marvin.routes._base.base_controllers import BaseUserController
from marvin.routes._base.controller import controller
from marvin.routes._base.mixins import HttpRepo
from marvin.routes._base import MarvinCrudRoute
from marvin.schemas.event.event import EventNotifierOptionsPagination, EventNotifierOptionsSummary
from marvin.schemas.mapper import cast
from marvin.schemas.response.pagination import PaginationQuery


from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import EventTypes, EventUserSignupData

router = APIRouter(prefix="/event", tags=["Event: Event Options"], route_class=MarvinCrudRoute)


@controller(router)
class EventsNotifierOptionsController(BaseUserController):
    event_bus: EventBusService = Depends(EventBusService.as_dependency)

    @cached_property
    def repo(self):
        if not self.user:
            raise Exception("No user is logged in.")

        return self.repos.event_notifier_options

    # =======================================================================
    # Notifier Options
    @router.get("/options", response_model=EventNotifierOptionsPagination)
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery)):
        response = self.repo.page_all(
            pagination=q,
            override=EventNotifierOptionsSummary,
        )

        self.event_bus.dispatch(
            integration_id="registration",
            group_id=self.user.group_id,
            event_type=EventTypes.webhook_task,
            document_data=EventUserSignupData(username=self.user.username, email=self.user.email),
        )

        response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return response
