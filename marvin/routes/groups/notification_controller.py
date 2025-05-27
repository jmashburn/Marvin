"""
This module defines the FastAPI controller for managing group-specific event
notification configurations within the Marvin application.

It provides endpoints for CRUD operations on group event notifiers and for
testing the notifier configurations.
"""

from functools import cached_property  # For lazy-loading properties

from fastapi import APIRouter, Depends, HTTPException, status  # Added status for HTTP_201_CREATED
from pydantic import UUID4  # For UUID type validation

# Marvin base controllers, schemas, and services
from marvin.routes._base import MarvinCrudRoute  # Custom route class
from marvin.routes._base.base_controllers import BaseUserController  # Base for user-auth routes
from marvin.routes._base.controller import controller  # CBV decorator
from marvin.routes._base.mixins import HttpRepo  # Mixin for CRUD HTTP handling
from marvin.schemas.group.event import (  # Pydantic schemas for group event notifiers
    GroupEventNotifierCreate,
    GroupEventNotifierPagination,
    GroupEventNotifierPrivate,  # Used for fetching full data including sensitive URLs
    GroupEventNotifierRead,
    GroupEventNotifierSave,  # Intermediate schema for creation logic
    GroupEventNotifierUpdate,
)
from marvin.schemas.mapper import cast  # Utility for casting between schema types
from marvin.schemas.response.pagination import PaginationQuery  # Pagination query parameters
from marvin.services.event_bus_service.event_bus_listener import AppriseEventListener  # For testing
from marvin.services.event_bus_service.event_bus_service import EventBusService  # Event bus dependency
from marvin.services.event_bus_service.event_types import (  # Event system components
    Event,
    EventBusMessage,
    EventDocumentDataBase,
    EventDocumentType,
    EventOperation,
    EventTypes,
)

# APIRouter for group event notifications, using MarvinCrudRoute for consistent header handling.
# All routes will be under /group/notifications.
router = APIRouter(prefix="/group/notifications", route_class=MarvinCrudRoute)


@controller(router)
class GroupEventsNotifierController(BaseUserController):
    """
    Controller for managing group-specific event notifier configurations.

    Provides CRUD endpoints for notifiers and an endpoint to send a test notification
    to a configured notifier. Requires user authentication for all operations.
    The operations are scoped to the current user's group.
    """

    # Dependency injection for the EventBusService
    event_bus: EventBusService = Depends(EventBusService.as_dependency)

    @cached_property
    def repo(self):  # Type hint could be GroupRepositoryGeneric[GroupEventNotifierRead, GroupEventNotifierModel, ...]
        """
        Provides a cached instance of the group event notifier repository.

        This repository (`self.repos.group_event_notifier`) is already scoped to the
        current user's group due to `BaseUserController`'s `repos` property.

        Raises:
            Exception: If no user is logged in (should be caught by BaseUserController).

        Returns:
            The group event notifier repository instance.
        """
        if not self.user:  # Should be handled by BaseUserController dependency
            raise Exception("No user is logged in. This should be caught by user dependency.")
        return self.repos.group_event_notifier

    # =======================================================================
    # CRUD Operations for Group Event Notifiers
    # =======================================================================

    @property
    def mixins(self) -> HttpRepo[GroupEventNotifierSave, GroupEventNotifierRead, GroupEventNotifierUpdate]:
        """
        Provides an instance of `HttpRepo` configured for Group Event Notifier CRUD operations.

        Initializes `HttpRepo` with the appropriate repository, logger, and exception handlers.
        Note the use of `GroupEventNotifierSave` as the create schema (C) type,
        `GroupEventNotifierRead` as the read schema (R), and `GroupEventNotifierUpdate`
        as the update schema (U).
        """
        # HttpRepo[CreateSchema, ReadSchema, UpdateSchema]
        return HttpRepo[GroupEventNotifierSave, GroupEventNotifierRead, GroupEventNotifierUpdate](
            self.repo,
            self.logger,
            self.registered_exceptions,
            "An unexpected error occurred with group event notifier.",  # Custom default error message
        )

    @router.get("", response_model=GroupEventNotifierPagination, summary="List Group Event Notifiers")
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery)) -> GroupEventNotifierPagination:
        """
        Retrieves a paginated list of event notifiers configured for the current user's group.

        Args:
            q (PaginationQuery): FastAPI dependency for pagination query parameters.

        Returns:
            GroupEventNotifierPagination: Paginated list of group event notifiers.
        """
        # `self.repo` is already group-scoped.
        paginated_response = self.repo.page_all(
            pagination=q,
            override_schema=GroupEventNotifierRead,  # Serialize items using GroupEventNotifierRead
        )
        # Set HATEOAS pagination guide URLs
        paginated_response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return paginated_response

    @router.post(
        "",
        response_model=GroupEventNotifierRead,
        status_code=status.HTTP_201_CREATED,
        summary="Create Group Event Notifier",
    )
    def create_one(self, data: GroupEventNotifierCreate) -> GroupEventNotifierRead:
        """
        Creates a new event notifier configuration for the current user's group.

        The `group_id` is automatically assigned based on the current user's group.

        Args:
            data (GroupEventNotifierCreate): Pydantic schema containing data for the new notifier.

        Returns:
            GroupEventNotifierRead: The Pydantic schema of the newly created notifier.
        """
        # Cast the input `GroupEventNotifierCreate` data to `GroupEventNotifierSave` schema,
        # injecting the current user's group_id. This prepares the data for the repository.
        save_data = cast(data, GroupEventNotifierSave, group_id=self.group_id)
        # Use the mixin's create_one method for standardized creation and error handling
        return self.mixins.create_one(save_data)

    @router.get("/{item_id}", response_model=GroupEventNotifierRead, summary="Get a Specific Group Event Notifier")
    def get_one(self, item_id: UUID4) -> GroupEventNotifierRead:
        """
        Retrieves a specific event notifier configuration by its ID.

        The notifier must belong to the current user's group.

        Args:
            item_id (UUID4): The unique identifier of the group event notifier.

        Returns:
            GroupEventNotifierRead: The Pydantic schema of the requested notifier.

        Raises:
            HTTPException (404 Not Found): If the notifier with the given ID is not found
                                         or does not belong to the user's group.
        """
        # `self.mixins.get_one` uses `self.repo` which is group-scoped.
        return self.mixins.get_one(item_id)

    @router.put("/{item_id}", response_model=GroupEventNotifierRead, summary="Update a Group Event Notifier")
    def update_one(self, item_id: UUID4, data: GroupEventNotifierUpdate) -> GroupEventNotifierRead:
        """
        Updates an existing event notifier configuration.

        If `data.apprise_url` is not provided in the update payload, the existing
        URL is preserved. This prevents accidental removal of the Apprise URL if only
        other fields (like name or enabled status) are being updated.
        The notifier must belong to the current user's group.

        Args:
            item_id (UUID4): The ID of the group event notifier to update.
            data (GroupEventNotifierUpdate): Pydantic schema with update data.

        Returns:
            GroupEventNotifierRead: The Pydantic schema of the updated notifier.

        Raises:
            HTTPException (404 Not Found): If the notifier is not found.
        """
        # If apprise_url is not included in the update request (is None),
        # fetch the current notifier's private data (which includes the URL)
        # and reuse the existing URL. This prevents accidental deletion of the URL.
        if data.apprise_url is None:
            # Fetch the existing item using a schema that includes the apprise_url
            current_data: GroupEventNotifierPrivate | None = self.repo.get_one(item_id, override_schema=GroupEventNotifierPrivate)
            if current_data:  # Should always be found if mixin.update_one is to succeed later
                data.apprise_url = current_data.apprise_url
            # If current_data is None, get_one in mixins.update_one will raise 404.

        # `self.mixins.update_one` uses `self.repo` which is group-scoped.
        return self.mixins.update_one(item_id=item_id, data=data)  # Corrected param order

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a Group Event Notifier")
    def delete_one(self, item_id: UUID4) -> None:  # Return None for 204
        """
        Deletes an event notifier configuration by its ID.

        The notifier must belong to the current user's group.

        Args:
            item_id (UUID4): The ID of the group event notifier to delete.

        Returns:
            None: HTTP 204 No Content on successful deletion.

        Raises:
            HTTPException (404 Not Found): If the notifier is not found.
        """
        # `self.mixins.delete_one` uses `self.repo` which is group-scoped.
        # The `type: ignore` was present in original; usually means a type mismatch perceived by the linter
        # but functionally correct. HttpRepo.delete_one returns R (GroupEventNotifierRead),
        # but FastAPI handles None return + 204 status code correctly.
        self.mixins.delete_one(item_id)  # type: ignore
        return None

    # =======================================================================
    # Test Event Notifications
    # =======================================================================

    # TODO: "properly re-implement this with new event listeners" - as per original code comment
    @router.post("/{item_id}/test", status_code=status.HTTP_204_NO_CONTENT, summary="Test a Group Event Notifier")
    def test_notification(self, item_id: UUID4) -> None:
        """
        Sends a test notification message to a specified group event notifier.

        This is used to verify that a configured notifier (e.g., an Apprise URL)
        is working correctly. The notifier must belong to the current user's group.

        Args:
            item_id (UUID4): The ID of the group event notifier to test.

        Returns:
            None: HTTP 204 No Content on successful dispatch of the test.

        Raises:
            HTTPException (404 Not Found): If the notifier is not found.
        """
        # Fetch the notifier configuration, ensuring it's the private schema to get apprise_url
        notifier_config: GroupEventNotifierPrivate | None = self.repo.get_one(item_id, override_schema=GroupEventNotifierPrivate)
        if not notifier_config:  # Should be caught by get_one if not found
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notifier configuration not found.")

        # Construct a test event payload
        event_type = EventTypes.test_message
        test_event_payload = Event(
            message=EventBusMessage.from_type(event_type, "This is a test message from Marvin."),
            event_type=event_type,
            integration_id="marvin_test_event_notification",  # Unique ID for this test event source
            document_data=EventDocumentDataBase(  # Basic document data for the event
                document_type=EventDocumentType.generic, operation=EventOperation.info
            ),
        )

        # Initialize a temporary AppriseEventListener for this test.
        # It's scoped to the current user's group_id.
        test_listener = AppriseEventListener(self.group_id)

        # Directly publish to the specific Apprise URL of the notifier being tested.
        # The `publish_to_subscribers` method here is used somewhat unconventionally
        # by passing a list containing just the single Apprise URL to test.
        try:
            test_listener.publish_to_subscribers(test_event_payload, [notifier_config.apprise_url])
            self.logger.info(f"Test notification sent to notifier ID {item_id} (URL: {notifier_config.apprise_url}) for group {self.group_id}")
        except Exception as e:
            self.logger.error(f"Failed to send test notification for notifier ID {item_id}: {e}")
            # Consider if an error response should be sent to the client here,
            # e.g., a 500 error if Apprise fails. Currently, it would still return 204.
            # For a more robust test, this might raise an HTTPException.
            # For now, matching original behavior of logging and returning 204 regardless of Apprise outcome.
            pass

        return None  # HTTP 204 No Content
