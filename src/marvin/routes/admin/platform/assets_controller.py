"""Admin assets controller."""

from functools import cached_property

from fastapi import APIRouter
from pydantic import UUID4

from marvin.repos.platform import AssetsRepository
from marvin.routes._base import BaseAdminController, controller
from marvin.routes._base.mixins import HttpRepo
from marvin.schemas.platform import AssetCreate, AssetRead

router = APIRouter(prefix="/assets")


@controller(router)
class AdminAssetsRoutes(BaseAdminController):
    """Controller for managing assets."""

    @cached_property
    def repo(self) -> AssetsRepository:
        """Get assets repository for current group."""
        if not self.user or not self.user.group_id:
            raise ValueError("User must have a group assigned")
        return AssetsRepository(self.session, self.user.group_id)

    @property
    def mixins(self) -> HttpRepo[AssetCreate, AssetRead, AssetCreate]:
        """Mixin for CRUD operations."""
        return HttpRepo[AssetCreate, AssetRead, AssetCreate](self.repo, self.logger, self.registered_exceptions)

    @router.get("", response_model=list[AssetRead], summary="List Assets")
    def get_all(self) -> list[AssetRead]:
        """Get all assets in the user's group."""
        assets = self.repo.get_all()
        return [self.repo.schema.from_orm(a) for a in assets]

    @router.post("", response_model=AssetRead, summary="Create Asset")
    def create(self, schema: AssetCreate) -> AssetRead:
        """Create a new asset."""
        return self.mixins.create_one(schema)

    @router.get("/{asset_id}", response_model=AssetRead, summary="Get Asset")
    def get_one(self, asset_id: UUID4) -> AssetRead:
        """Get a specific asset."""
        return self.mixins.get_one(asset_id)

    @router.delete("/{asset_id}", response_model=AssetRead, summary="Delete Asset")
    def delete(self, asset_id: UUID4) -> AssetRead:
        """Delete an asset."""
        return self.mixins.delete_one(asset_id)
