"""Admin resources controller."""

from functools import cached_property

from fastapi import APIRouter
from pydantic import UUID4

from marvin.repos.platform import ResourcesRepository
from marvin.routes._base import BaseAdminController, controller
from marvin.routes._base.mixins import HttpRepo
from marvin.schemas.platform import ResourceCreate, ResourceRead, ResourceUpdate

router = APIRouter(prefix="/resources")


@controller(router)
class AdminResourcesRoutes(BaseAdminController):
    """Controller for managing resources."""

    @cached_property
    def repo(self) -> ResourcesRepository:
        """Get resources repository for current group."""
        if not self.user or not self.user.group_id:
            raise ValueError("User must have a group assigned")
        return ResourcesRepository(self.session, self.user.group_id)

    @property
    def mixins(self) -> HttpRepo[ResourceCreate, ResourceRead, ResourceUpdate]:
        """Mixin for CRUD operations."""
        return HttpRepo[ResourceCreate, ResourceRead, ResourceUpdate](self.repo, self.logger, self.registered_exceptions)

    @router.get("", response_model=list[ResourceRead], summary="List Resources")
    def get_all(self) -> list[ResourceRead]:
        """Get all resources in the user's group."""
        resources = self.repo.get_all()
        return [self.repo.schema.from_orm(r) for r in resources]

    @router.post("", response_model=ResourceRead, summary="Create Resource")
    def create(self, schema: ResourceCreate) -> ResourceRead:
        """Create a new resource."""
        return self.mixins.create(schema)

    @router.get("/{resource_id}", response_model=ResourceRead, summary="Get Resource")
    def get_one(self, resource_id: UUID4) -> ResourceRead:
        """Get a specific resource."""
        return self.mixins.get_one(resource_id)

    @router.put("/{resource_id}", response_model=ResourceRead, summary="Update Resource")
    def update(self, resource_id: UUID4, schema: ResourceUpdate) -> ResourceRead:
        """Update a resource."""
        schema.id = resource_id
        return self.mixins.update(schema)

    @router.delete("/{resource_id}", summary="Delete Resource")
    def delete(self, resource_id: UUID4) -> dict:
        """Delete a resource."""
        return self.mixins.delete(resource_id)
