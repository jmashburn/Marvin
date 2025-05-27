"""
This module defines the FastAPI controller for administrative management of user groups
within the Marvin application.

It provides RESTful endpoints for administrators to perform CRUD (Create, Read,
Update, Delete) operations on groups, including managing group preferences.
"""

from functools import cached_property  # For lazy-loading properties

from fastapi import APIRouter, Depends, HTTPException, status  # Core FastAPI components
from pydantic import UUID4  # For UUID type validation

# Marvin specific schemas and services
from marvin.schemas.group import GroupCreate, GroupPagination, GroupRead
from marvin.schemas.group.group import GroupAdminUpdate  # Schema for updating group by admin
from marvin.schemas.mapper import mapper  # Utility for mapping data between objects
from marvin.schemas.response.pagination import PaginationQuery  # For handling pagination parameters
from marvin.schemas.response.responses import ErrorResponse  # Standardized error response
from marvin.services.group.group_service import GroupService  # Service layer for group operations

# Base controller and mixin for CRUD helpers
from .._base import BaseAdminController, controller
from .._base.mixins import HttpRepo

# APIRouter for admin group management, prefixed with /groups
# All routes here will be under /admin/groups.
router = APIRouter(prefix="/groups")


@controller(router)
class AdminGroupManagementRoutes(BaseAdminController):
    """
    Controller for administrative CRUD operations on user groups.

    Provides endpoints for creating, retrieving, updating, and deleting groups.
    Includes logic for handling group preferences and ensuring data integrity,
    such as preventing deletion of groups with active users.
    All operations require administrator privileges.
    """

    @cached_property
    def repo(self):  # Type hint could be RepositoryGroup if available and imported
        """
        Provides a cached instance of the groups repository (`self.repos.groups`).

        Ensures that a user is logged in before accessing the repository.
        The repository instance is specific to group management.

        Raises:
            Exception: If no user is logged in (should be caught by BaseAdminController).

        Returns:
            The groups repository instance.
        """
        if not self.user:  # Should be handled by BaseAdminController dependency
            raise Exception("No user is logged in. This should be caught by admin dependency.")
        return self.repos.groups

    # =======================================================================
    # CRUD Operations via HttpRepo Mixin and Custom Methods
    # =======================================================================

    @property
    def mixins(self) -> HttpRepo[GroupCreate, GroupRead, GroupAdminUpdate]:
        """
        Provides a cached instance of `HttpRepo` configured for Group CRUD operations.

        This property initializes `HttpRepo` with the group repository, logger,
        and registered exception messages, streamlining common CRUD HTTP responses
        and error handling.
        """
        # The type variables for HttpRepo:
        # C (CreateSchema) = GroupCreate
        # R (ReadSchema)   = GroupRead
        # U (UpdateSchema) = GroupAdminUpdate
        return HttpRepo[GroupCreate, GroupRead, GroupAdminUpdate](
            self.repo,  # The groups repository from the cached_property above
            self.logger,
            self.registered_exceptions,  # Method from BaseUserController to get error messages
        )

    @router.get("", response_model=GroupPagination, summary="Get All Groups (Paginated)")
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery)) -> GroupPagination:
        """
        Retrieves a paginated list of all groups.

        Administrators can use this endpoint to view all groups in the system.
        Supports standard pagination query parameters.

        Args:
            q (PaginationQuery): FastAPI dependency for pagination query parameters
                                 (page, per_page, order_by, etc.).

        Returns:
            GroupPagination: A Pydantic model containing the list of groups for the
                             current page and pagination metadata.
        """
        # Use the repository's page_all method for pagination
        paginated_response = self.repo.page_all(
            pagination=q,
            override_schema=GroupRead,  # Ensure response items are serialized as GroupRead
        )
        # Set HATEOAS pagination guide URLs for client navigation
        paginated_response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return paginated_response

    @router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED, summary="Create a New Group")
    def create_one(self, data: GroupCreate) -> GroupRead:
        """
        Creates a new group.

        This endpoint delegates group creation to the `GroupService`, which
        handles business logic such as slug generation and ensuring uniqueness.
        Accessible only by administrators.

        Args:
            data (GroupCreate): Pydantic schema containing the data for the new group
                                (e.g., name).

        Returns:
            GroupRead: The Pydantic schema of the newly created group.
        """
        # Group creation logic is handled by the GroupService
        return GroupService.create_group(self.repos, data)

    @router.get("/{item_id}", response_model=GroupRead, summary="Get a Specific Group by ID")
    def get_one(self, item_id: UUID4) -> GroupRead:
        """
        Retrieves a specific group by its unique ID.

        Accessible only by administrators.

        Args:
            item_id (UUID4): The unique identifier of the group to retrieve.

        Returns:
            GroupRead: The Pydantic schema of the requested group.

        Raises:
            HTTPException (404 Not Found): If no group with the given ID exists.
        """
        # Uses the get_one method from the HttpRepo mixin for standardized fetching and error handling
        return self.mixins.get_one(item_id)

    @router.put("/{item_id}", response_model=GroupRead, summary="Update a Group")
    def update_one(self, item_id: UUID4, data: GroupAdminUpdate) -> GroupRead:
        """
        Updates an existing group's details, including its name and preferences.

        If `data.preferences` is provided, the group's preferences are updated.
        If `data.name` is provided and different from the current name, the group's
        name (and consequently its slug, handled by the repository) is updated.
        Accessible only by administrators.

        Args:
            item_id (UUID4): The ID of the group to update.
            data (GroupAdminUpdate): Pydantic schema containing the update data.
                                     Fields not provided will not be changed (partial update).

        Returns:
            GroupRead: The Pydantic schema of the updated group.

        Raises:
            HTTPException (404 Not Found): If the group or its preferences are not found.
        """
        # Retrieve the existing group model instance
        group_model_instance = self.repo.get_one_raw(item_id)  # Assuming get_one_raw returns the SQLAlchemy model
        if not group_model_instance:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group not found.")

        # Update group preferences if provided in the request data
        if data.preferences:
            # Fetch existing preferences for the group
            preferences_model = self.repos.group_preferences.get_one_raw(value=item_id, key="group_id")
            if not preferences_model:
                # This case might indicate data inconsistency or preferences are not yet created.
                # Depending on design, could create preferences here or raise error.
                # For now, assume preferences should exist if group exists and are being updated.
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group preferences not found for this group.")

            # Map incoming preference data to the existing preferences model
            updated_preferences_data = mapper(data.preferences, preferences_model)
            # Update preferences in the database
            # The group_model_instance.preferences will be updated by the relationship if correctly configured
            # or by direct assignment after the update.
            self.repos.group_preferences.update(preferences_model.id, updated_preferences_data)  # Update by preference ID

        # Update group name if it's provided and different from the current name
        # The repository's update method should handle slug regeneration if name changes.
        if data.name is not None and data.name.strip() and data.name != group_model_instance.name:
            # Prepare data dictionary for group update
            group_update_dict = {"name": data.name}
            # Update the group using the repository. This will also handle slug update.
            group_model_instance = self.repo.update(item_id, group_update_dict)

        # After all updates, refresh the group_model_instance to get the latest state
        # and convert to the response schema.
        # If repo.update already returns the schema, this explicit get might be redundant.
        # However, to ensure all changes (name, preferences via relationship) are reflected:
        self.session.refresh(group_model_instance)  # Refresh to capture potential relationship updates
        return self.repo.schema.model_validate(group_model_instance)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a Group")
    def delete_one(self, item_id: UUID4) -> None:
        """
        Deletes a group by its unique ID.

        A group cannot be deleted if it still has users associated with it.
        Accessible only by administrators.

        Args:
            item_id (UUID4): The ID of the group to delete.

        Raises:
            HTTPException (404 Not Found): If the group with the given ID does not exist.
            HTTPException (400 Bad Request): If the group still has associated users.
        """
        # Retrieve the group to check for associated users
        group_to_delete = self.repo.get_one(item_id)  # Returns Pydantic model
        if not group_to_delete:  # Should be caught by get_one if not found
            # This is defensive; mixins.get_one would typically raise 404.
            # If it returns None, this ensures correct 404.
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group not found.")

        # Check if the group has any associated users.
        # This requires the GroupRead schema or underlying model to have user count/list.
        # Assuming `group_to_delete.users` is available from the schema/model.
        # If `self.repo.get_one` doesn't load users, an explicit fetch might be needed:
        # db_group = self.repo.get_one_raw(item_id)
        # num_users = len(db_group.users) # Accessing SQLAlchemy model's relationship
        # For now, assuming GroupRead from self.repo.get_one has `users` field or similar.
        # This check might need adjustment based on actual schema/repo capabilities.

        # A more direct way using the repository for users count:
        user_count_in_group = self.repos.users.count_all(match_key="group_id", match_value=item_id)

        if user_count_in_group > 0:
            # Prevent deletion if group has users
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond(message="Cannot delete a group that still has users assigned to it."),
            )

        # If no users, proceed with deletion using the mixin
        self.mixins.delete_one(item_id)
        # HTTP 204 No Content response is automatically handled by FastAPI for None return with this status code.
        return None
