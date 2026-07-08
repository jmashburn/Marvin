"""Resource routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import ResourceCreate, ResourceRead, ResourceUpdate
from marvin.services.event_bus_service.event_types import EventOperation, EventResourceData, EventTypes

router = APIRouter(prefix="/resources")


@controller(router)
class ResourcesController(BaseUserController):
    """Authenticated CRUD routes for resources."""

    @router.get("", response_model=list[ResourceRead], summary="List Resources")
    def list_resources(self) -> list[ResourceRead]:
        return self.repos.resources.get_all(order_by="name")

    @router.post("", response_model=ResourceRead, status_code=status.HTTP_201_CREATED, summary="Create Resource")
    def create_resource(self, data: ResourceCreate) -> ResourceRead:
        # Inject created_by and group_id from authenticated user
        data_dict = data.model_dump()
        data_dict["created_by"] = self.user.id
        data_dict["group_id"] = self.group_id
        resource = self.repos.resources.create(data_dict)

        # Emit event
        self.event_bus.dispatch(
            integration_id="resource_management",
            group_id=self.group_id,
            event_type=EventTypes.resource_created,
            document_data=EventResourceData(
                operation=EventOperation.create,
                resource_id=resource.id,
                resource_name=resource.name,
                resource_slug=resource.slug,
                resource_type=resource.resource_type,
                workspace_id=self.group_id,
                url=resource.url,
            ),
            message=f"Resource '{resource.name}' created",
        )

        return resource

    @router.get("/{item_id}", response_model=ResourceRead, summary="Get Resource")
    def get_resource(self, item_id: UUID4) -> ResourceRead:
        resource = self.repos.resources.get_one(item_id)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
        return resource

    @router.patch("/{item_id}", response_model=ResourceRead, summary="Update Resource")
    def update_resource(self, item_id: UUID4, data: ResourceUpdate) -> ResourceRead:
        if not self.repos.resources.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

        resource = self.repos.resources.update(item_id, data)

        # Emit event
        self.event_bus.dispatch(
            integration_id="resource_management",
            group_id=self.group_id,
            event_type=EventTypes.resource_updated,
            document_data=EventResourceData(
                operation=EventOperation.update,
                resource_id=resource.id,
                resource_name=resource.name,
                resource_slug=resource.slug,
                resource_type=resource.resource_type,
                workspace_id=self.group_id,
                url=resource.url,
            ),
            message=f"Resource '{resource.name}' updated",
        )

        return resource

    @router.delete("/{item_id}", summary="Delete Resource")
    def delete_resource(self, item_id: UUID4) -> dict:
        resource = self.repos.resources.get_one(item_id)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

        # Emit event before deletion
        self.event_bus.dispatch(
            integration_id="resource_management",
            group_id=self.group_id,
            event_type=EventTypes.resource_deleted,
            document_data=EventResourceData(
                operation=EventOperation.delete,
                resource_id=resource.id,
                resource_name=resource.name,
                resource_slug=resource.slug,
                resource_type=resource.resource_type,
                workspace_id=self.group_id,
                url=resource.url,
            ),
            message=f"Resource '{resource.name}' deleted",
        )

        self.repos.resources.delete(item_id)
        return {"status": "ok", "message": "Resource deleted successfully"}
