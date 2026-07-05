"""Asset routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import AssetCreate, AssetRead

router = APIRouter(prefix="/assets")


@controller(router)
class AssetsController(BaseUserController):
    """Authenticated CRUD routes for assets (metadata only, file upload deferred to Phase 7)."""

    @router.get("", response_model=list[AssetRead], summary="List Assets")
    def list_assets(self) -> list[AssetRead]:
        return self.repos.assets.get_all(order_by="name")

    @router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED, summary="Create Asset Metadata")
    def create_asset(self, data: AssetCreate) -> AssetRead:
        """
        Create asset metadata entry.

        Note: This endpoint only creates the metadata record. File upload functionality
        (multipart form-data) is planned for Phase 7. For testing, provide a file_path
        that points to an existing file or use a placeholder path.
        """
        # Inject uploaded_by from authenticated user
        data_dict = data.model_dump()
        data_dict["uploaded_by"] = self.user.id
        return self.repos.assets.create(data_dict)

    @router.get("/{item_id}", response_model=AssetRead, summary="Get Asset")
    def get_asset(self, item_id: UUID4) -> AssetRead:
        asset = self.repos.assets.get_one(item_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return asset

    @router.patch("/{item_id}", response_model=AssetRead, summary="Update Asset Metadata")
    def update_asset(self, item_id: UUID4, data: AssetCreate) -> AssetRead:
        """Update asset metadata (dimensions, alt text, description, etc)."""
        if not self.repos.assets.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return self.repos.assets.update(item_id, data)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Asset")
    def delete_asset(self, item_id: UUID4) -> None:
        """Delete asset metadata. Note: Physical file deletion is deferred to Phase 7."""
        if not self.repos.assets.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        self.repos.assets.delete(item_id)
