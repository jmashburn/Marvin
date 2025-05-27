"""
This module defines the FastAPI controller for managing event notifier options
within the Marvin application.

It provides endpoints for users to retrieve information about available
event notification options.
"""

from functools import cached_property  # For lazy-loading properties

from fastapi import APIRouter, Depends  # Core FastAPI components

# from pydantic import UUID4 # UUID4 was imported but not used in the current code
# Marvin base controllers and schema imports
from marvin.routes._base import MarvinCrudRoute  # Custom route class for CRUD-like routes
from marvin.routes._base.base_controllers import BaseUserController  # Base controller for user-authenticated routes
from marvin.routes._base.controller import controller  # Decorator for class-based views
from marvin.schemas.event.event import (  # Pydantic schemas for event notifier options
    EventNotifierOptionsPagination,
    EventNotifierOptionsSummary,
)
from marvin.schemas.response.pagination import PaginationQuery  # For handling pagination parameters

# Event bus service and types for dispatching events
from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import (
    EventTypes,
    EventUserSignupData,  # This specific data type seems misused for a generic GET all options.
)

# APIRouter for event notifier options, using MarvinCrudRoute for consistent header handling.
# All routes here will be under /event.
router = APIRouter(prefix="/event", route_class=MarvinCrudRoute)


@controller(router)
class EventsNotifierOptionsController(BaseUserController):
    """
    Controller for managing and retrieving event notifier options.

    Provides endpoints for users to list available notification options.
    Requires user authentication for access.
    """

    # Dependency injection for the EventBusService
    event_bus: EventBusService = Depends(EventBusService.as_dependency)

    @cached_property
    def repo(self):  # Type hint could be RepositoryGeneric[EventNotifierOptionsSummary, EventNotifierOptionsModel]
        """
        Provides a cached instance of the event notifier options repository.

        Ensures that a user is logged in before accessing the repository.
        The repository instance is used for data access operations related to
        event notifier options.

        Raises:
            Exception: If no user is logged in (should be caught by BaseUserController).

        Returns:
            The event notifier options repository instance.
        """
        if not self.user:  # Should be handled by BaseUserController dependency
            raise Exception("No user is logged in. This should be caught by user dependency.")
        # Accesses the generic repository for event_notifier_options
        return self.repos.event_notifier_options

    # =======================================================================
    # Notifier Options Endpoints
    # =======================================================================
    @router.get("/options", response_model=EventNotifierOptionsPagination, summary="Get All Event Notifier Options (Paginated)")
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery)) -> EventNotifierOptionsPagination:
        """
        Retrieves a paginated list of all available event notifier options.

        NOTE: This endpoint currently dispatches an event (`EventTypes.webhook_task`
        with `EventUserSignupData`) upon being called. This is unusual for a GET
        request and might be unintended or indicative of a placeholder/debug behavior,
        as GET requests should typically be idempotent and free of side effects.

        Args:
            q (PaginationQuery): FastAPI dependency for pagination query parameters
                                 (page, per_page, order_by, etc.).

        Returns:
            EventNotifierOptionsPagination: A Pydantic model containing the list of
                                            event notifier options for the current page
                                            and pagination metadata.
        """
        # Retrieve paginated data from the repository
        paginated_response = self.repo.page_all(
            pagination=q,
            override_schema=EventNotifierOptionsSummary,  # Ensure response items are serialized as Summary
        )

        # Dispatch an event - THIS IS UNUSUAL FOR A GET ENDPOINT
        # It uses EventUserSignupData which seems mismatched for an endpoint listing notifier options.
        # This might be placeholder, debug code, or a misunderstanding of its purpose.
        # Consider reviewing if this event dispatch is intended here.
        try:
            self.event_bus.dispatch(
                integration_id="get_event_notifier_options",  # More descriptive integration_id
                group_id=self.user.group_id,  # Assuming user context is relevant for the event
                event_type=EventTypes.webhook_task,  # This event type might not be appropriate
                document_data=EventUserSignupData(username=self.user.username, email=self.user.email),  # Data seems mismatched
                message="Retrieved event notifier options.",  # Clarified message
            )
            self.logger.info(f"Event dispatched after retrieving event notifier options by user {self.user.username}")
        except Exception as e:
            self.logger.error(f"Failed to dispatch event during get_all_event_notifier_options: {e}")

        # Set HATEOAS pagination guide URLs for client navigation
        paginated_response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return paginated_response
