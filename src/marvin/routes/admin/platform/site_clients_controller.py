"""Admin site clients controller."""

from functools import cached_property

from fastapi import APIRouter, Depends
from pydantic import UUID4

from marvin.schemas.platform import SiteClientCreate, SiteClientRead, SiteClientUpdate
from marvin.repos.platform import SiteClientsRepository
from marvin.routes._base import BaseAdminController, controller
from marvin.routes._base.mixins import HttpRepo

router = APIRouter(prefix="/site-clients")


@controller(router)
class AdminSiteClientsRoutes(BaseAdminController):
    """Controller for managing site clients."""

    @cached_property
    def repo(self) -> SiteClientsRepository:
        """Get site clients repository for current group."""
        if not self.user or not self.user.group_id:
            raise ValueError("User must have a group assigned")
        return SiteClientsRepository(self.session, self.user.group_id)

    @property
    def mixins(self) -> HttpRepo[SiteClientCreate, SiteClientRead, SiteClientUpdate]:
        """Mixin for CRUD operations."""
        return HttpRepo[SiteClientCreate, SiteClientRead, SiteClientUpdate](
            self.repo, self.logger, self.registered_exceptions
        )

    @router.get("", response_model=list[SiteClientRead], summary="List Site Clients")
    def get_all(self) -> list[SiteClientRead]:
        """Get all site clients in the user's group."""
        clients = self.repo.get_all()
        return [self.repo.schema.from_orm(c) for c in clients]

    @router.post("", response_model=SiteClientRead, summary="Create Site Client")
    def create(self, schema: SiteClientCreate) -> SiteClientRead:
        """Create a new site client."""
        return self.mixins.create(schema)

    @router.get("/{client_id}", response_model=SiteClientRead, summary="Get Site Client")
    def get_one(self, client_id: UUID4) -> SiteClientRead:
        """Get a specific site client."""
        return self.mixins.get_one(client_id)

    @router.put("/{client_id}", response_model=SiteClientRead, summary="Update Site Client")
    def update(self, client_id: UUID4, schema: SiteClientUpdate) -> SiteClientRead:
        """Update a site client."""
        schema.id = client_id
        return self.mixins.update(schema)

    @router.delete("/{client_id}", summary="Delete Site Client")
    def delete(self, client_id: UUID4) -> dict:
        """Delete a site client."""
        return self.mixins.delete(client_id)
