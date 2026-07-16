"""
This module defines the FastAPI controller for managing group-specific event
notification configurations within the Marvin application.

It provides endpoints for CRUD operations on group event notifiers and for
testing the notifier configurations.
"""

from functools import cached_property  # For lazy-loading properties

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status  # Added status for HTTP_201_CREATED
from pydantic import UUID4  # For UUID type validation
from sqlalchemy import desc, select

# Marvin base controllers, schemas, and services
from marvin.core.config import get_app_settings  # For checking Apprise availability
from marvin.db.models.groups.notification_execution_logs import NotificationExecutionLogModel
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
    NotificationExecutionLogRead,
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
from marvin.services.event_bus_service.publisher import _log_notification_execution

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

    def _check_apprise_available(self) -> None:
        """
        Verifies that Apprise is enabled and available.

        Raises:
            HTTPException (503 Service Unavailable): If Apprise is not enabled or configured.
        """
        settings = get_app_settings()
        if not settings.APPRISE_READY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Apprise notification service is not enabled or configured. "
                "Please enable APPRISE_ENABLED in settings to use notifications.",
            )

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
        self._check_apprise_available()
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
        self._check_apprise_available()
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
        self._check_apprise_available()
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
        self._check_apprise_available()
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

    @router.delete("/{item_id}", summary="Delete a Group Event Notifier")
    def delete_one(self, item_id: UUID4) -> dict:
        """
        Deletes an event notifier configuration by its ID.

        The notifier must belong to the current user's group.

        Args:
            item_id (UUID4): The ID of the group event notifier to delete.

        Returns:
            dict: Status message on successful deletion.

        Raises:
            HTTPException (404 Not Found): If the notifier is not found.
        """
        self._check_apprise_available()
        self.mixins.delete_one(item_id)  # type: ignore
        return {"status": "ok", "message": "Event notifier deleted successfully"}

    # =======================================================================
    # Test Event Notifications
    # =======================================================================

    @router.get("/{item_id}/logs", response_model=list[NotificationExecutionLogRead], summary="Get Notification Execution Logs")
    def get_notification_logs(self, item_id: UUID4, limit: int = 50) -> list[NotificationExecutionLogRead]:
        """Returns the most recent execution log entries for a notifier."""
        self._check_apprise_available()
        stmt = (
            select(NotificationExecutionLogModel)
            .where(NotificationExecutionLogModel.notifier_id == item_id)
            .order_by(desc(NotificationExecutionLogModel.executed_at))
            .limit(limit)
        )
        rows = self.repos.session.execute(stmt).scalars().all()
        return [NotificationExecutionLogRead.model_validate(r) for r in rows]

    # TODO: "properly re-implement this with new event listeners" - as per original code comment
    @router.post("/{item_id}/test", summary="Test a Group Event Notifier")
    def test_notification(self, item_id: UUID4) -> dict:
        """
        Sends a test notification message to a specified group event notifier.

        This is used to verify that a configured notifier (e.g., an Apprise URL)
        is working correctly. The notifier must belong to the current user's group.

        Args:
            item_id (UUID4): The ID of the group event notifier to test.

        Returns:
            dict: Status message on successful dispatch of the test.

        Raises:
            HTTPException (404 Not Found): If the notifier is not found.
        """
        self._check_apprise_available()
        # Fetch the notifier configuration, ensuring it's the private schema to get apprise_url
        notifier_config: GroupEventNotifierPrivate | None = self.repo.get_one(item_id, override_schema=GroupEventNotifierPrivate)
        if not notifier_config:  # Should be caught by get_one if not found
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notifier configuration not found.")

        event_type = EventTypes.test_message
        test_event_payload = Event(
            message=EventBusMessage.from_type(
                event_type,
                f"Test from Marvin — notification '{notifier_config.name}' is working correctly."
            ),
            event_type=event_type,
            integration_id="marvin_test_event_notification",
            workspace_id=self.group_id,
            document_data=EventDocumentDataBase(
                document_type=EventDocumentType.generic, operation=EventOperation.info
            ),
        )

        try:
            from marvin.services.secrets.resolver import resolve
            resolved_url = resolve(notifier_config.apprise_url, group_id=self.group_id)
            enriched_urls = AppriseEventListener.update_urls_with_event_data([resolved_url], test_event_payload)
            # Publish directly — the publisher will log the attempt with notifier_id/group_id
            from marvin.services.event_bus_service.publisher import ApprisePublisher
            publisher = ApprisePublisher()
            publisher.publish(
                test_event_payload,
                enriched_urls,
                notifier_id=item_id,
                group_id=self.group_id,
                event_type="test_message",
            )
            self.logger.info(f"Test notification sent to notifier ID {item_id} for group {self.group_id}")
        except Exception as e:
            self.logger.error(f"Failed to send test notification for notifier ID {item_id}: {e}")
            _log_notification_execution(
                notifier_id=item_id,
                group_id=self.group_id,
                status="failed",
                event_type="test_message",
                error_message=str(e),
                request_payload={"title": test_event_payload.message.title, "body": test_event_payload.message.body},
            )

        return {"status": "ok", "message": "Test notification sent successfully"}
