"""API client routes."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.db_setup import generate_session
from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import APIClientCreate, APIClientRead, APIClientUpdate, APIClientWithToken
from marvin.schemas.publishing import SiteConfiguration, WorkspaceInfo, WorkspaceSiteInfo

router = APIRouter(prefix="/api-clients")


@controller(router)
class APIClientsController(BaseUserController):
    """Authenticated CRUD routes for API clients."""

    @router.get("", response_model=list[APIClientRead], summary="List API Clients")
    def list_api_clients(self) -> list[APIClientRead]:
        """List all API clients for the current workspace."""
        return self.repos.api_clients.get_all(order_by="name")

    @router.post("", response_model=APIClientWithToken, status_code=status.HTTP_201_CREATED, summary="Create API Client")
    def create_api_client(self, data: APIClientCreate) -> APIClientWithToken:
        """
        Create a new API client.

        IMPORTANT: The token is returned ONCE. Store it securely.
        """
        # Inject created_by field (current user)
        data_dict = data.model_dump() if not isinstance(data, dict) else data
        data_dict["created_by"] = self.user.id
        return self.repos.api_clients.create(data_dict)

    @router.get("/{item_id}", response_model=APIClientRead, summary="Get API Client")
    def get_api_client(
        self,
        item_id: str = Path(
            ...,
            description="API client UUID or slug",
            openapi_examples={
                "uuid": {"summary": "UUID", "value": "123e4567-e89b-12d3-a456-426614174000"},
                "slug": {"summary": "Slug", "value": "my-site-client"},
            },
        ),
    ) -> APIClientRead:
        """Get a specific API client by ID or slug."""
        # Try UUID first, then slug
        try:
            from uuid import UUID

            UUID(item_id)
            api_client = self.repos.api_clients.get_one(item_id)
        except (ValueError, AttributeError):
            # Not a valid UUID, try as slug
            api_client = self.repos.api_clients.get_by_slug(item_id)

        if not api_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API client not found.")
        return api_client

    @router.patch("/{item_id}", response_model=APIClientRead, summary="Update API Client")
    def update_api_client(
        self,
        item_id: str = Path(
            ...,
            description="API client UUID or slug",
            openapi_examples={
                "uuid": {"summary": "UUID", "value": "123e4567-e89b-12d3-a456-426614174000"},
                "slug": {"summary": "Slug", "value": "my-site-client"},
            },
        ),
        data: APIClientUpdate = ...,
    ) -> APIClientRead:
        """Update an API client by ID or slug."""
        # Try UUID first, then slug
        try:
            from uuid import UUID

            UUID(item_id)
            api_client = self.repos.api_clients.get_one(item_id)
        except (ValueError, AttributeError):
            api_client = self.repos.api_clients.get_by_slug(item_id)

        if not api_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API client not found.")
        return self.repos.api_clients.update(api_client.id, data)

    @router.delete("/{item_id}", summary="Delete API Client")
    def delete_api_client(
        self,
        item_id: str = Path(
            ...,
            description="API client UUID or slug",
            openapi_examples={
                "uuid": {"summary": "UUID", "value": "123e4567-e89b-12d3-a456-426614174000"},
                "slug": {"summary": "Slug", "value": "my-site-client"},
            },
        ),
    ) -> dict:
        """Delete an API client by ID or slug."""
        # Try UUID first, then slug
        try:
            from uuid import UUID

            UUID(item_id)
            api_client = self.repos.api_clients.get_one(item_id)
        except (ValueError, AttributeError):
            api_client = self.repos.api_clients.get_by_slug(item_id)

        if not api_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API client not found.")
        self.repos.api_clients.delete(api_client.id)
        return {"status": "ok", "message": "API client deleted successfully"}

    @router.post("/{item_id}/rotate-token", response_model=APIClientWithToken, summary="Rotate API Client Token")
    def rotate_api_client_token(
        self,
        item_id: str = Path(
            ...,
            description="API client UUID or slug",
            openapi_examples={
                "uuid": {"summary": "UUID", "value": "123e4567-e89b-12d3-a456-426614174000"},
                "slug": {"summary": "Slug", "value": "my-site-client"},
            },
        ),
    ) -> APIClientWithToken:
        """
        Rotate/regenerate the token for an API client by ID or slug.

        The old token is invalidated immediately.
        The new token is returned ONCE. Store it securely.
        """
        # Try UUID first, then slug
        try:
            from uuid import UUID

            UUID(item_id)
            api_client = self.repos.api_clients.get_one(item_id)
        except (ValueError, AttributeError):
            api_client = self.repos.api_clients.get_by_slug(item_id)

        if not api_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API client not found.")

        return self.repos.api_clients.rotate_token(api_client.id)

    @router.get("/{item_id}/preview", response_model=WorkspaceSiteInfo, summary="Preview Publishing API Payload")
    def preview_publish_payload(
        self,
        item_id: str = Path(
            ...,
            description="API client UUID or slug",
            openapi_examples={
                "uuid": {"summary": "UUID", "value": "123e4567-e89b-12d3-a456-426614174000"},
                "slug": {"summary": "Slug", "value": "my-site-client"},
            },
        ),
        session: Session = Depends(generate_session),
    ) -> WorkspaceSiteInfo:
        """
        Preview what external consumer would receive from publishing API.

        Returns the same payload as /api/publish/{workspace_slug}/site but uses
        admin session authentication instead of requiring a site client token.

        This allows logged-in admins to verify what external sites will receive
        without needing to copy tokens.

        Args:
            item_id: The UUID or slug of the API client
            session: Database session (injected)

        Returns:
            WorkspaceSiteInfo: Combined workspace and site configuration

        Raises:
            HTTPException: 404 if API client not found
        """
        # Try UUID first, then slug
        try:
            from uuid import UUID

            UUID(item_id)
            api_client = self.repos.api_clients.get_one(item_id)
        except (ValueError, AttributeError):
            api_client = self.repos.api_clients.get_by_slug(item_id)

        if not api_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API client not found.")

        # Get the workspace for this API client
        from marvin.db.models.groups import Groups, GroupPreferencesModel

        group = session.query(Groups).filter(Groups.id == api_client.group_id).first()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found for this API client.")

        # Get group preferences (includes site configuration)
        prefs = session.query(GroupPreferencesModel).filter(GroupPreferencesModel.group_id == group.id).first()

        # Build site configuration from preferences (with sensible defaults)
        site_config = SiteConfiguration(
            title=prefs.site_title if prefs and prefs.site_title else group.name,
            tagline=prefs.site_tagline if prefs else None,
            description=prefs.site_description if prefs else None,
            canonical_url=prefs.site_canonical_url if prefs else None,
            logo=prefs.site_logo if prefs else None,
            favicon=prefs.site_favicon if prefs else None,
            locale=prefs.site_locale if prefs and prefs.site_locale else "en-US",
            timezone=prefs.site_timezone if prefs and prefs.site_timezone else "America/New_York",
            contact_email=prefs.site_contact_email if prefs else None,
            social=prefs.site_social_json if prefs else None,
            metadata=prefs.site_metadata_json if prefs else None,
        )

        # Build workspace info
        workspace_info = WorkspaceInfo(
            slug=group.slug,
            name=group.name,
        )

        return WorkspaceSiteInfo(
            workspace=workspace_info,
            site=site_config,
        )
