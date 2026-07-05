"""Collection routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import CollectionCreate, CollectionRead, CollectionUpdate

router = APIRouter(prefix="/collections")


@controller(router)
class CollectionsController(BaseUserController):
    """Authenticated CRUD routes for collections."""

    @router.get("", response_model=list[CollectionRead], summary="List Collections")
    def list_collections(self) -> list[CollectionRead]:
        return self.repos.collections.get_all(order_by="name")

    @router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED, summary="Create Collection")
    def create_collection(self, data: CollectionCreate) -> CollectionRead:
        return self.repos.collections.create(data)

    @router.get("/{item_id}", response_model=CollectionRead, summary="Get Collection")
    def get_collection(self, item_id: UUID4) -> CollectionRead:
        collection = self.repos.collections.get_one(item_id)
        if not collection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
        return collection

    @router.patch("/{item_id}", response_model=CollectionRead, summary="Update Collection")
    def update_collection(self, item_id: UUID4, data: CollectionUpdate) -> CollectionRead:
        if not self.repos.collections.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
        return self.repos.collections.update(item_id, data)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Collection")
    def delete_collection(self, item_id: UUID4) -> None:
        if not self.repos.collections.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
        self.repos.collections.delete(item_id)
