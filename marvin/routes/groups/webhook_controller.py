"""
This module defines the FastAPI controller for managing group-specific webhooks
within the Marvin application.

It provides endpoints for CRUD operations on webhooks, as well as utilities
for re-running all scheduled webhooks for the day and testing individual webhooks.
"""

from datetime import UTC, datetime, time  # Added time for type hint
from functools import cached_property  # For lazy-loading properties

from fastapi import APIRouter, BackgroundTasks, Depends, status  # Added status for HTTP_201_CREATED
from pydantic import UUID4  # For UUID type validation

# Marvin base controllers, schemas, services, and utilities
from marvin.routes._base.base_controllers import BaseUserController
from marvin.routes._base.controller import controller
from marvin.routes._base.mixins import HttpRepo
from marvin.schemas.group.webhook import (  # Pydantic schemas for webhooks
    WebhookCreate,
    WebhookPagination,
    WebhookRead,  # WebhookUpdate is available but HttpRepo mixin is typed with WebhookCreate for updates
)
from marvin.schemas.response.pagination import PaginationQuery  # Pagination query parameters

# Services for webhook execution logic
from marvin.services.scheduler.tasks.post_webhooks import post_group_webhooks, post_single_webhook

# EventDocumentType was imported but not used in the current code.
# from marvin.services.event_bus_service.event_types import EventDocumentType

# APIRouter for group webhooks. All routes will be under /groups/webhooks.
router = APIRouter(prefix="/groups/webhooks")


@controller(router)
class WebhookReadController(BaseUserController):  # Consider renaming to WebhookController if it handles full CRUD
    """
    Controller for managing webhook configurations for the current user's group.

    Provides full CRUD (Create, Read, Update, Delete) functionality for webhooks,
    along with endpoints to manually trigger or test webhooks. All operations
    are scoped to the authenticated user's group.
    """

    @cached_property
    def repo(self):  # Type hint could be GroupRepositoryGeneric[WebhookRead, WebhookModel, ...]
        """
        Provides a cached instance of the webhooks repository (`self.repos.webhooks`).
        This repository is scoped to the current user's group.
        """
        return self.repos.webhooks

    @property
    def mixins(self) -> HttpRepo[WebhookCreate, WebhookRead, WebhookCreate]:  # HttpRepo[C, R, U]
        """
        Provides an instance of `HttpRepo` configured for Webhook CRUD operations.

        Note: The Update schema (U) is currently specified as `WebhookCreate`.
        This might be intentional if update operations expect the same fields as creation,
        or it could be an area for review if `WebhookUpdate` is intended for updates.
        """
        # HttpRepo[CreateSchema, ReadSchema, UpdateSchema]
        # Currently, UpdateSchema is WebhookCreate. If WebhookUpdate is the intended schema for updates,
        # this should be HttpRepo[WebhookCreate, WebhookRead, WebhookUpdate].
        return HttpRepo[WebhookCreate, WebhookRead, WebhookCreate](
            self.repo,
            self.logger,
            # Assuming registered_exceptions is available from BaseUserController
            # self.registered_exceptions
        )

    @router.get("", response_model=WebhookPagination, summary="List Webhooks for Group")
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery)) -> WebhookPagination:
        """
        Retrieves a paginated list of webhooks configured for the current user's group.

        Args:
            q (PaginationQuery): FastAPI dependency for pagination query parameters.

        Returns:
            WebhookPagination: Paginated list of webhooks.
        """
        # `self.repo` is already group-scoped by BaseUserController logic.
        paginated_response = self.repo.page_all(
            pagination=q,
            override_schema=WebhookRead,  # Ensure items are serialized as WebhookRead
        )
        paginated_response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return paginated_response

    @router.post("", response_model=WebhookRead, status_code=status.HTTP_201_CREATED, summary="Create a Webhook for Group")
    def create_one(self, data: WebhookCreate) -> WebhookRead:
        """
        Creates a new webhook configuration for the current user's group.

        The `group_id` is automatically assigned based on the current user's group.
        The input `WebhookCreate` data is cast to `WebhookUpdate` before creation;
        this might be part of a specific data processing pipeline or could be simplified
        if `WebhookCreate` is directly usable by the repository.
        (Note: Original code casts to WebhookUpdate, but mixin is typed with WebhookCreate for C.
        This suggests `WebhookCreate` is indeed the intended input for the repo's create method here.)

        Args:
            data (WebhookCreate): Pydantic schema containing data for the new webhook.

        Returns:
            WebhookRead: The Pydantic schema of the newly created webhook.
        """
        # The original code casts `data` (WebhookCreate) to `WebhookUpdate` then to `WebhookCreate` for the mixin.
        # This seems circuitous. If `WebhookCreate` is the correct input for `repo.create`,
        # and `group_id` needs to be added, it's better to create a new `WebhookCreate` instance
        # or modify a dict representation.
        # Assuming the goal is to ensure group_id is set:
        save_data_dict = data.model_dump()
        save_data_dict["group_id"] = self.group_id  # Ensure group_id is set for the current user's group

        # Use WebhookCreate as the input type for create_one as per mixin typing.
        # If the repository expects a model with group_id already set, this is correct.
        # The original `mapper.cast(data, WebhookUpdate, group_id=self.group_id)` was unusual.
        # A more direct approach if `WebhookCreate` can take `group_id`:
        # save_payload = WebhookCreate(**data.model_dump(), group_id=self.group_id)
        # For now, matching the spirit of ensuring group_id is part of the data sent to repo.create:
        # The mixin is HttpRepo[WebhookCreate, WebhookRead, WebhookCreate], so C is WebhookCreate.
        # The repo's create method will expect a WebhookCreate compatible dict or object.
        create_payload = WebhookCreate(**save_data_dict)
        return self.mixins.create_one(create_payload)

    @router.get("/rerun", summary="Re-run All Scheduled Webhooks for Today", status_code=status.HTTP_202_ACCEPTED)
    def rerun_webhooks(self) -> dict[str, str]:
        """
        Manually re-fires all previously scheduled webhooks for the current day
        for the user's group.

        This triggers a background task to post group webhooks starting from the
        beginning of the current UTC day.

        Returns:
            dict[str, str]: A message indicating the process has been initiated.
        """
        # Determine the start of the current UTC day
        start_of_day_utc: time = datetime.min.time()  # Midnight
        start_datetime_utc: datetime = datetime.combine(datetime.now(UTC).date(), start_of_day_utc)

        # Dispatch the task to post group webhooks for the current group
        # This is a fire-and-forget style, actual execution happens in background.
        # TODO: Consider if `post_group_webhooks` should be an async task managed by BackgroundTasks
        # for better handling if it's a long-running process. For now, it's called synchronously.
        post_group_webhooks(start_dt=start_datetime_utc, group_id=self.group.id)
        self.logger.info(f"Manual rerun of webhooks initiated for group ID {self.group.id} for today.")
        return {"message": "Re-running scheduled webhooks for today has been initiated."}

    @router.get("/{item_id}", response_model=WebhookRead, summary="Get a Specific Webhook")
    def get_one(self, item_id: UUID4) -> WebhookRead:
        """
        Retrieves a specific webhook configuration by its ID.

        The webhook must belong to the current user's group.

        Args:
            item_id (UUID4): The unique identifier of the webhook.

        Returns:
            WebhookRead: The Pydantic schema of the requested webhook.
        """
        return self.mixins.get_one(item_id)

    @router.get("/{item_id}/test", summary="Test a Specific Webhook", status_code=status.HTTP_202_ACCEPTED)
    def test_one(self, item_id: UUID4, bg_tasks: BackgroundTasks) -> dict[str, str]:
        """
        Sends a test request to a specific webhook configuration.

        The test is performed as a background task to avoid blocking the request.
        The webhook must belong to the current user's group.

        Args:
            item_id (UUID4): The ID of the webhook to test.
            bg_tasks (BackgroundTasks): FastAPI dependency for running background tasks.

        Returns:
            dict[str, str]: A message indicating that the test has been scheduled.
        """
        webhook_to_test = self.mixins.get_one(item_id)  # Fetches WebhookRead schema
        # Add the actual webhook posting as a background task
        bg_tasks.add_task(post_single_webhook, webhook_to_test, "Test Webhook from Marvin")
        self.logger.info(f"Test for webhook ID {item_id} scheduled in background.")
        return {"message": f"Test for webhook '{webhook_to_test.name or item_id}' has been scheduled."}

    @router.put("/{item_id}", response_model=WebhookRead, summary="Update a Webhook")
    def update_one(self, item_id: UUID4, data: WebhookCreate) -> WebhookRead:  # data type is WebhookCreate
        """
        Updates an existing webhook configuration.

        The webhook must belong to the current user's group.
        Note: The input data schema is `WebhookCreate`. If partial updates are desired
        or if `WebhookUpdate` schema exists and is different, this might need adjustment.
        The mixin is currently typed as `HttpRepo[WebhookCreate, WebhookRead, WebhookCreate]`,
        meaning `WebhookCreate` is also used as the Update schema type `U` for the mixin.

        Args:
            item_id (UUID4): The ID of the webhook to update.
            data (WebhookCreate): Pydantic schema with the update data.
                                  (Typically an Update schema like `WebhookUpdate` would be used here).

        Returns:
            WebhookRead: The Pydantic schema of the updated webhook.
        """
        # The mixin's update_one method is called. It expects data of type U, which is WebhookCreate here.
        return self.mixins.update_one(item_id=item_id, data=data)  # Corrected param order

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a Webhook")
    def delete_one(self, item_id: UUID4) -> None:  # Return None for 204
        """
        Deletes a webhook configuration by its ID.

        The webhook must belong to the current user's group.

        Args:
            item_id (UUID4): The ID of the webhook to delete.

        Returns:
            None: HTTP 204 No Content on successful deletion.
        """
        # The type: ignore was in the original, likely due to mixin's delete_one returning R (WebhookRead)
        # but FastAPI handles None return + 204 status code correctly.
        self.mixins.delete_one(item_id)  # type: ignore
        return None
