"""Asset routes."""

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import UUID4
from slugify import slugify

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import AssetBulkUploadResult, AssetRead, AssetUpdate, AssetUploadRequest
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
            metadata_json=metadata_dict,
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
            document_data=EventAssetData.from_schema(
                asset,
                workspace_id=self.group_id,
                workspace_name=self.group.name if self.group else None,
                uploader_id=self.user.id if self.user else None,
                uploader_name=self.user.full_name if self.user else None,
            ),
            message=f"Asset {asset.name} uploaded",
        )

        return asset

    @router.post("/bulk-upload", response_model=AssetBulkUploadResult, status_code=status.HTTP_201_CREATED,
                 summary="Bulk Upload Assets")
    async def bulk_upload_assets(
        self,
        files: list[UploadFile] = File(...),
        attach_to: str | None = Form(None),
    ) -> AssetBulkUploadResult:
        """Upload several files at once (native multipart) and, optionally, attach them to an entry.

        When `attach_to` is set the images fill that entry type's recipe roles by position (first →
        hero, the rest → gallery), then the recipe's per-role `derive` steps run to fulfill it from
        what was uploaded — e.g. one hero yields a cropped `thumbnail` — so a single upload can meet
        a recipe that wants more. Anything the recipe still requires but nothing could supply (a
        required gallery photo has no source to derive from) comes back in `unmet` for a human.
        """
        import uuid

        storage = get_storage_provider()
        asset_service = AssetStorageService(self.repos, storage)

        created: list[AssetRead] = []
        for f in files:
            base = (f.filename or "upload").rsplit("/", 1)[-1]
            name = base.rsplit(".", 1)[0] or "upload"
            slug = f"{slugify(name) or 'asset'}-{uuid.uuid4().hex[:6]}"
            asset = asset_service.upload_asset(
                upload_file=f,
                upload_request=AssetUploadRequest(slug=slug, name=name),
                group_id=self.group_id, user_id=self.user.id,
            )
            self.event_bus.dispatch(
                integration_id="asset_management", group_id=self.group_id,
                event_type=EventTypes.asset_uploaded,
                document_data=EventAssetData.from_schema(
                    asset, workspace_id=self.group_id,
                    workspace_name=self.group.name if self.group else None,
                    uploader_id=self.user.id if self.user else None,
                    uploader_name=self.user.full_name if self.user else None,
                ),
                message=f"Asset {asset.name} uploaded",
            )
            created.append(asset)

        result = AssetBulkUploadResult(assets=created)
        if not attach_to or not created:
            return result

        from marvin.db.models.platform.entries import Entries
        from marvin.services.ai.entity_resolve import resolve_entity_id
        from marvin.services.assets.asset_derivation_service import AssetDerivationService
        from marvin.services.entries import EntryService

        entry_id = resolve_entity_id(self.session, self.group_id, "entry", attach_to)
        entry = self.session.get(Entries, entry_id) if entry_id else None
        if not entry or entry.group_id != self.group_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entry '{attach_to}' not found.")

        roles = self._recipe_roles(entry)
        svc = EntryService(self.session, self.group_id, event_bus=self.event_bus, actor_id=self.user.id)
        for j, asset in enumerate(created):
            role = roles[j] if j < len(roles) else (roles[-1] if roles else None)
            status_ = svc.attach_asset(entry_id, asset.id, role=role)
            result.attached.append({"asset_id": str(asset.id), "role": role, "status": status_})
        result.attached_to = str(attach_to)

        fulfilled = AssetDerivationService(self.repos, storage).fulfill_for_entry(
            entry, self.group_id, self.user.id, event_bus=self.event_bus,
        )
        result.derived = fulfilled["derived"]
        result.unmet = fulfilled["unmet"]
        return result

    def _recipe_roles(self, entry) -> list:
        """The entry type's declared asset roles (e.g. [hero, gallery]) for role-by-position attach."""
        from marvin.db.models.platform.entry_types import EntryTypes
        from marvin.schemas.platform.entry_type_recipe import EntryTypeRecipe

        et = self.session.get(EntryTypes, entry.entry_type_id)
        recipe = EntryTypeRecipe.model_validate((et.recipe_json if et else {}) or {})
        return [r.role for r in recipe.assets.roles] if (recipe.assets and recipe.assets.roles) else []

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

        # Use exclude_none=False to allow explicit null values to clear fields
        # exclude_unset=True only excludes fields not sent in the request
        updated_asset = self.repos.assets.update(item_id, data.model_dump(exclude_unset=True, exclude_none=False))

        # Emit event
        self.event_bus.dispatch(
            integration_id="asset_management",
            group_id=self.group_id,
            event_type=EventTypes.asset_updated,
            document_data=EventAssetData.from_schema(
                AssetRead.model_validate(updated_asset),
                workspace_id=self.group_id,
                workspace_name=self.group.name if self.group else None,
                uploader_id=self.user.id if self.user else None,
                uploader_name=self.user.full_name if self.user else None,
            ),
            message=f"Asset {updated_asset.name} updated",
        )

        return updated_asset

    @router.post("/{item_id}/apply-suggestion", response_model=AssetRead, summary="Apply AI Suggestion")
    def apply_suggestion(self, item_id: UUID4) -> AssetRead:
        """Apply the asset's staged AI suggestion (suggestion_json) and clear it."""
        if not self.repos.assets.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return self.repos.assets.apply_suggestion(item_id)

    @router.post("/{item_id}/reject-suggestion", response_model=AssetRead, summary="Reject AI Suggestion")
    def reject_suggestion(self, item_id: UUID4) -> AssetRead:
        """Discard the asset's staged AI suggestion without applying it."""
        if not self.repos.assets.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return self.repos.assets.clear_suggestion(item_id)

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
            document_data=EventAssetData.from_schema(
                AssetRead.model_validate(asset),
                workspace_id=self.group_id,
                workspace_name=self.group.name if self.group else None,
                uploader_id=self.user.id if self.user else None,
                uploader_name=self.user.full_name if self.user else None,
            ),
            message=f"Asset {asset.name} deleted",
        )

        return {"status": "ok", "message": "Asset deleted successfully"}

    @router.get("/{item_id}/file", summary="Serve Asset File")
    def serve_asset_file(self, item_id: UUID4):
        """
        Serve the actual asset file content directly.

        For local storage, serves the file from disk.
        For S3 storage, redirects to the public URL or signed URL.
        """
        from fastapi.responses import FileResponse, RedirectResponse
        from pathlib import Path

        asset = self.repos.assets.get_one(item_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

        # For local storage, serve file directly
        if asset.storage_provider == "local":
            storage_provider = get_storage_provider()
            file_path = Path(storage_provider.root) / asset.storage_key

            if not file_path.exists():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset file not found on disk.")

            return FileResponse(path=str(file_path), media_type=asset.mime_type or "application/octet-stream", filename=asset.original_filename)

        # For remote providers, redirect to computed URL from current config
        return RedirectResponse(url=get_storage_provider().get_public_url(asset.storage_key))
