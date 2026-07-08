"""Asset routes."""

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import AssetCreate, AssetRead, AssetUpdate, AssetUploadRequest
from marvin.services.assets.asset_storage_service import AssetStorageService
from marvin.services.event_bus_service.event_types import EventAssetData, EventTypes
from marvin.services.storage.provider_factory import get_storage_provider

router = APIRouter(prefix="/assets")


@controller(router)
class AssetsController(BaseUserController):
    """Authenticated CRUD routes for assets with file upload support."""

    @router.get("", response_model=list[AssetRead], summary="List Assets")
    def list_assets(self) -> list[AssetRead]:
        return self.repos.assets.get_all(order_by="name")

    @router.post("/upload", response_model=AssetRead, status_code=status.HTTP_201_CREATED, summary="Upload Asset")
    async def upload_asset(
        self,
        file: UploadFile = File(...),
        slug: str = Form(...),
        name: str = Form(...),
        alt_text: str | None = Form(None),
        description: str | None = Form(None),
        metadata: str | None = Form(None),
    ) -> AssetRead:
        """
        Upload a new asset file.

        Accepts multipart/form-data with:
        - file: The binary file
        - slug: URL-friendly identifier
        - name: Display name
        - alt_text: Accessibility text (optional)
        - description: Description (optional)
        - metadata: JSON string of custom metadata (optional)

        Server automatically extracts:
        - MIME type, file size, checksum
        - Image dimensions (width, height, orientation)
        - Asset type classification
        """
        # Parse metadata JSON if provided
        metadata_dict = None
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON in metadata field.")

        # Create upload request
        upload_request = AssetUploadRequest(
            slug=slug,
            name=name,
            alt_text=alt_text,
            description=description,
            metadata_=metadata_dict,
        )

        # Get storage provider and create service
        storage_provider = get_storage_provider()
        asset_service = AssetStorageService(self.repos, storage_provider)

        # Upload through service
        asset = asset_service.upload_asset(
            upload_file=file,
            upload_request=upload_request,
            group_id=self.group_id,
            user_id=self.user.id,
        )

        # Emit event
        self.event_bus.dispatch(
            integration_id="asset_management",
            group_id=self.group_id,
            event_type=EventTypes.asset_uploaded,
            document_data=EventAssetData.from_schema(asset),
            message=f"Asset {asset.name} uploaded",
        )

        return asset

    @router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED, summary="Create Asset Metadata")
    def create_asset(self, data: AssetCreate) -> AssetRead:
        """
        Create asset metadata entry.

        Note: This endpoint only creates the metadata record. File upload functionality
        (multipart form-data) is planned for Phase 7. For testing, provide a file_path
        that points to an existing file or use a placeholder path.
        """
        # Inject uploaded_by and group_id from authenticated user
        data_dict = data.model_dump()
        data_dict["uploaded_by"] = self.user.id
        data_dict["group_id"] = self.group_id
        return self.repos.assets.create(data_dict)

    @router.get("/{item_id}", response_model=AssetRead, summary="Get Asset")
    def get_asset(self, item_id: UUID4) -> AssetRead:
        asset = self.repos.assets.get_one(item_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return asset

    @router.patch("/{item_id}", response_model=AssetRead, summary="Update Asset Metadata")
    def update_asset(self, item_id: UUID4, data: AssetUpdate) -> AssetRead:
        """
        Update asset metadata (slug, name, alt text, description, metadata).

        Note: Technical metadata (MIME type, dimensions, checksum, etc) cannot be changed.
        """
        if not self.repos.assets.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

        updated_asset = self.repos.assets.update(item_id, data.model_dump(exclude_unset=True))

        # Emit event
        self.event_bus.dispatch(
            integration_id="asset_management",
            group_id=self.group_id,
            event_type=EventTypes.asset_updated,
            document_data=EventAssetData.from_schema(AssetRead.model_validate(updated_asset)),
            message=f"Asset {updated_asset.name} updated",
        )

        return updated_asset

    @router.delete("/{item_id}", summary="Delete Asset")
    def delete_asset(self, item_id: UUID4) -> dict:
        """Delete asset from storage and database."""
        asset = self.repos.assets.get_one(item_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

        # Delete through service to remove from storage too
        storage_provider = get_storage_provider()
        asset_service = AssetStorageService(self.repos, storage_provider)

        asset_service.delete_asset(item_id)

        # Emit event
        self.event_bus.dispatch(
            integration_id="asset_management",
            group_id=self.group_id,
            event_type=EventTypes.asset_deleted,
            document_data=EventAssetData.from_schema(AssetRead.model_validate(asset)),
            message=f"Asset {asset.name} deleted",
        )

        return {"status": "ok", "message": "Asset deleted successfully"}
