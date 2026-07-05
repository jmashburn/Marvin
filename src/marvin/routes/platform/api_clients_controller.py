"""API client routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import APIClientCreate, APIClientRead, APIClientUpdate, APIClientWithToken

router = APIRouter(prefix="/api-clients")


@controller(router)
class APIClientsController(BaseUserController):
    """Authenticated CRUD routes for API clients."""

    @router.get("", response_model=list[APIClientRead], summary="List API Clients")
    def list_api_clients(self) -> list[APIClientRead]:
        """List all API clients for the current workspace."""
        return self.repos.api_clients.get_all(order_by="name")

    @router.post(
        "",
        response_model=APIClientWithToken,
        status_code=status.HTTP_201_CREATED,
        summary="Create API Client"
    )
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
    def get_api_client(self, item_id: UUID4) -> APIClientRead:
        """Get a specific API client by ID."""
        api_client = self.repos.api_clients.get_one(item_id)
        if not api_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API client not found."
            )
        return api_client

    @router.patch("/{item_id}", response_model=APIClientRead, summary="Update API Client")
    def update_api_client(self, item_id: UUID4, data: APIClientUpdate) -> APIClientRead:
        """Update an API client."""
        if not self.repos.api_clients.get_one(item_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API client not found."
            )
        return self.repos.api_clients.update(item_id, data)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete API Client")
    def delete_api_client(self, item_id: UUID4) -> None:
        """Delete an API client."""
        if not self.repos.api_clients.get_one(item_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API client not found."
            )
        self.repos.api_clients.delete(item_id)

    @router.post(
        "/{item_id}/rotate-token",
        response_model=APIClientWithToken,
        summary="Rotate API Client Token"
    )
    def rotate_api_client_token(self, item_id: UUID4) -> APIClientWithToken:
        """
        Rotate/regenerate the token for an API client.

        The old token is invalidated immediately.
        The new token is returned ONCE. Store it securely.
        """
        return self.repos.api_clients.rotate_token(item_id)
