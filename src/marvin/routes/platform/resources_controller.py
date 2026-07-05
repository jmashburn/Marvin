"""Resource routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import ResourceCreate, ResourceRead, ResourceUpdate

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
        return self.repos.resources.create(data_dict)

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
        return self.repos.resources.update(item_id, data)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Resource")
    def delete_resource(self, item_id: UUID4) -> None:
        if not self.repos.resources.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
        self.repos.resources.delete(item_id)
