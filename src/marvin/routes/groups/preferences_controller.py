"""
This module defines the FastAPI controller for managing group-specific preferences
within the Marvin application.

It provides endpoints for retrieving and updating workspace site settings
via group preferences.
"""

from functools import cached_property

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import MarvinCrudRoute
from marvin.routes._base.base_controllers import BaseUserController
from marvin.routes._base.controller import controller
from marvin.schemas.group.preferences import (
    GroupPreferencesRead,
    GroupPreferencesUpdate,
)

# APIRouter for group preferences
router = APIRouter(prefix="/groups/{group_id}/preferences", route_class=MarvinCrudRoute)


@controller(router)
class GroupPreferencesController(BaseUserController):
    """
    Controller for managing workspace site settings via group preferences.

    Provides endpoints for getting and updating workspace preferences including
    site configuration fields. Requires user authentication and appropriate
    workspace access for all operations.
    """

    @cached_property
    def repo(self):
        """
        Provides a cached instance of the group preferences repository.

        Raises:
            Exception: If no user is logged in.

        Returns:
            The group preferences repository instance.
        """
        if not self.user:
            raise Exception("No user is logged in. This should be caught by user dependency.")
        return self.repos.group_preferences

    @router.get("", response_model=GroupPreferencesRead, summary="Get Workspace Preferences")
    def get_preferences(self, group_id: UUID4) -> GroupPreferencesRead:
        """
        Get workspace preferences including site settings.

        Retrieves all preference settings for the specified workspace, including
        site configuration fields like title, tagline, logo, etc.

        Args:
            group_id: The UUID of the workspace

        Returns:
            GroupPreferencesRead: The complete preferences including site settings

        Raises:
            HTTPException: 404 if workspace not found or user lacks access
            HTTPException: 403 if user doesn't have access to this workspace
        """
        # Verify user has access to this workspace
        if not self._user_has_workspace_access(group_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this workspace.",
            )

        # Get the preferences for this group
        preferences = self.repo.get_one(group_id=group_id)

        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preferences not found for workspace {group_id}",
            )

        return preferences

    @router.patch("", response_model=GroupPreferencesRead, summary="Update Workspace Preferences")
    def update_preferences(self, group_id: UUID4, data: GroupPreferencesUpdate) -> GroupPreferencesRead:
        """
        Update workspace preferences (requires ADMIN or OWNER role).

        Updates preference settings for the specified workspace. All fields are optional
        for partial updates. Site configuration fields include title, tagline, logo, etc.

        Args:
            group_id: The UUID of the workspace
            data: The preference fields to update

        Returns:
            GroupPreferencesRead: The updated preferences

        Raises:
            HTTPException: 404 if workspace not found
            HTTPException: 403 if user doesn't have ADMIN/OWNER access
        """
        # Verify user has admin/owner access to this workspace
        if not self._user_has_admin_access(group_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a workspace ADMIN or OWNER to update preferences.",
            )

        # Get existing preferences
        preferences = self.repo.get_one(group_id=group_id)

        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preferences not found for workspace {group_id}",
            )

        # Update the preferences ID in the update schema
        data.id = preferences.id
        data.group_id = group_id

        # Update and return
        return self.repo.update(data.id, data)

    def _user_has_workspace_access(self, group_id: UUID4) -> bool:
        """
        Check if the current user has access to the specified workspace.

        Users have access if they are:
        - A SUPER_ADMIN
        - A member of the workspace

        Args:
            group_id: The UUID of the workspace to check

        Returns:
            bool: True if user has access, False otherwise
        """
        # SUPER_ADMIN has access to all workspaces
        if self.user.is_super_admin:
            return True

        # Check if user is a member of this workspace
        # Note: This assumes user.workspace_memberships relationship exists
        # If not, we need to query the workspace_members table directly
        return any(membership.group_id == group_id for membership in self.user.workspace_memberships)

    def _user_has_admin_access(self, group_id: UUID4) -> bool:
        """
        Check if the current user has admin/owner access to the specified workspace.

        Users have admin access if they are:
        - A SUPER_ADMIN
        - An OWNER or ADMIN of the workspace

        Args:
            group_id: The UUID of the workspace to check

        Returns:
            bool: True if user has admin access, False otherwise
        """
        # SUPER_ADMIN has access to all workspaces
        if self.user.is_super_admin:
            return True

        # Check if user is an ADMIN or OWNER of this workspace
        for membership in self.user.workspace_memberships:
            if membership.group_id == group_id:
                # WorkspaceRole enum: OWNER=5, ADMIN=4
                return membership.workspace_role.value >= 4

        return False
