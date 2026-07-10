"""
Schemas for workspace member management.

Defines request/response schemas for adding, updating, and viewing
workspace memberships.
"""

from pydantic import UUID4, ConfigDict

from marvin.db.models.users.roles import WorkspaceRole
from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.user.user import UserSummary


class WorkspaceMemberCreate(_MarvinModel):
    """
    Schema for adding a user to a workspace.

    Used when a workspace admin wants to invite a user to their workspace.
    """

    user_id: UUID4
    """The ID of the user to add to the workspace."""

    workspace_role: WorkspaceRole
    """The role to assign (OWNER, ADMIN, EDITOR, AUTHOR, VIEWER)."""


class WorkspaceMemberUpdate(_MarvinModel):
    """
    Schema for updating a workspace member's role.

    Used when changing a user's permissions within a workspace.
    """

    workspace_role: WorkspaceRole
    """The new role to assign."""


class WorkspaceMemberWithUser(_MarvinModel):
    """
    Extended workspace membership schema with full user details.

    Used in list views to show member information alongside their role.
    """

    id: UUID4
    """Unique identifier for the membership."""

    user_id: UUID4
    """ID of the user."""

    group_id: UUID4
    """ID of the workspace (group)."""

    workspace_role: WorkspaceRole
    """The role this user has within this workspace."""

    user: UserSummary
    """Full user details (username, email, etc.)."""

    model_config = ConfigDict(from_attributes=True)
