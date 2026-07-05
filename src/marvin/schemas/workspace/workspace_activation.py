"""
Schemas for workspace activation (switching between workspaces).
"""

from pydantic import UUID4

from marvin.db.models.users.roles import WorkspaceRole
from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.group.group import GroupRead


class WorkspaceActivationRequest(_MarvinModel):
    """Request to change active workspace."""

    workspace_id: UUID4
    """The workspace to activate."""


class WorkspaceWithMembership(_MarvinModel):
    """Workspace with user's role and active status."""

    workspace: GroupRead
    """The workspace details."""
    role: WorkspaceRole
    """The user's role in this workspace."""
    is_active: bool
    """True if this is the user's currently active workspace."""
