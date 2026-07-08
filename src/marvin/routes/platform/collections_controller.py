"""Collection routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import CollectionCreate, CollectionRead, CollectionUpdate
from marvin.services.event_bus_service.event_types import EventCollectionData, EventOperation, EventTypes

router = APIRouter(prefix="/collections")


@controller(router)
class CollectionsController(BaseUserController):
    """Authenticated CRUD routes for collections."""

    @router.get("", response_model=list[CollectionRead], summary="List Collections")
    def list_collections(self) -> list[CollectionRead]:
        return self.repos.collections.get_all(order_by="name")

    @router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED, summary="Create Collection")
    def create_collection(self, data: CollectionCreate) -> CollectionRead:
        collection = self.repos.collections.create(data)

        # Emit event
        self.event_bus.dispatch(
            integration_id="collection_management",
            group_id=self.group_id,
            event_type=EventTypes.collection_created,
            document_data=EventCollectionData(
                operation=EventOperation.create,
                collection_id=collection.id,
                collection_name=collection.name,
                workspace_id=collection.group_id,
            ),
            message=f"Collection '{collection.name}' created",
            user_id=self.user.id if self.user else None,
            entity_id=collection.id,
            entity_type="collection",
        )

        return collection

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

        collection = self.repos.collections.update(item_id, data)

        # Emit event
        self.event_bus.dispatch(
            integration_id="collection_management",
            group_id=self.group_id,
            event_type=EventTypes.collection_updated,
            document_data=EventCollectionData(
                operation=EventOperation.update,
                collection_id=collection.id,
                collection_name=collection.name,
                workspace_id=collection.group_id,
            ),
            message=f"Collection '{collection.name}' updated",
            user_id=self.user.id if self.user else None,
            entity_id=collection.id,
            entity_type="collection",
        )

        return collection

    @router.delete("/{item_id}", summary="Delete Collection")
    def delete_collection(self, item_id: UUID4) -> dict:
        collection = self.repos.collections.get_one(item_id)
        if not collection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")

        # Emit event before deletion
        self.event_bus.dispatch(
            integration_id="collection_management",
            group_id=self.group_id,
            event_type=EventTypes.collection_deleted,
            document_data=EventCollectionData(
                operation=EventOperation.delete,
                collection_id=collection.id,
                collection_name=collection.name,
                workspace_id=collection.group_id,
            ),
            message=f"Collection '{collection.name}' deleted",
            user_id=self.user.id if self.user else None,
            entity_id=collection.id,
            entity_type="collection",
        )

        self.repos.collections.delete(item_id)
        return {"status": "ok", "message": "Collection deleted successfully"}
