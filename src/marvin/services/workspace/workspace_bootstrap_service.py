"""
Service for bootstrapping new workspaces with default content.
"""

from pydantic import UUID4

from marvin.db.models.groups import Groups
from marvin.db.models.users.roles import PlatformRole, WorkspaceRole
from marvin.repos.repository_factory import AllRepositories


class WorkspaceBootstrapService:
    """
    Static service for bootstrapping newly created workspaces.

    Creates default entry types, collections, and workspace memberships
    to make a workspace immediately usable.
    """

    # Default entry types to create
    DEFAULT_ENTRY_TYPES = [
        {
            "slug": "page",
            "name": "Page",
            "description": "Static pages and content",
            "icon": "📄",
            "color": "#4A90E2",
            "sort_order": 1,
            "is_system": True,
        },
        {
            "slug": "post",
            "name": "Post",
            "description": "Blog posts and updates",
            "icon": "📝",
            "color": "#50C878",
            "sort_order": 2,
            "is_system": True,
        },
        {
            "slug": "project",
            "name": "Project",
            "description": "Projects and case studies",
            "icon": "🚀",
            "color": "#FF6B6B",
            "sort_order": 3,
            "is_system": True,
        },
    ]

    # Default collections to create
    DEFAULT_COLLECTIONS = [
        {
            "slug": "featured",
            "name": "Featured",
            "description": "Featured content",
            "sort_order": 1,
        },
        {
            "slug": "recent",
            "name": "Recent",
            "description": "Recently published content",
            "sort_order": 2,
        },
    ]

    @staticmethod
    def bootstrap(repos: AllRepositories, workspace: Groups, creator_id: UUID4) -> None:
        """
        Bootstrap a newly created workspace with default content.

        Creates:
        1. Default entry types (page, post, project)
        2. Default collections (featured, recent)
        3. Workspace memberships (creator as OWNER, all admins as ADMIN)

        Args:
            repos: Repository factory for database access
            workspace: The newly created workspace
            creator_id: The user ID of the workspace creator
        """
        # 1. Create default entry types
        from marvin.db.models.platform.entry_types import EntryTypes

        for entry_type_data in WorkspaceBootstrapService.DEFAULT_ENTRY_TYPES:
            entry_type = EntryTypes(
                session=repos.session,
                group_id=workspace.id,
                **entry_type_data,
            )
            repos.session.add(entry_type)

        # 2. Create default collections
        from marvin.db.models.platform.collections import Collections

        for collection_data in WorkspaceBootstrapService.DEFAULT_COLLECTIONS:
            collection = Collections(
                session=repos.session,
                group_id=workspace.id,
                **collection_data,
            )
            repos.session.add(collection)

        # 3. Add creator as OWNER
        repos.workspace_members.add_member(
            user_id=creator_id,
            workspace_id=workspace.id,
            role=WorkspaceRole.OWNER,
        )

        # 4. Add all SUPER_ADMIN users as ADMIN (for convenience)
        from marvin.db.models.users.users import Users
        from sqlalchemy import select

        stmt = select(Users).where(Users.platform_role == PlatformRole.SUPER_ADMIN)
        super_admins = repos.session.execute(stmt).scalars().all()

        for admin_user in super_admins:
            # Skip if this is the creator (already added as OWNER)
            if admin_user.id == creator_id:
                continue

            try:
                repos.workspace_members.add_member(
                    user_id=admin_user.id,
                    workspace_id=workspace.id,
                    role=WorkspaceRole.ADMIN,
                )
            except Exception:
                # Skip if already a member (shouldn't happen, but be defensive)
                repos.session.rollback()
                continue

        # Flush changes but don't commit (caller will commit)
        repos.session.flush()
