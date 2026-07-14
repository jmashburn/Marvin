"""Entry repositories."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from marvin.db.models.platform import Entries, EntryTypes, EntryCollections, EntryAssets, EntryResources
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import EntryRead
from marvin.schemas.platform.entry_type_schema import EntryTypeSchemaDefinition
from marvin.services.content_validator import ContentValidationError, ContentValidator


class EntriesRepository(GroupRepositoryGeneric[EntryRead, Entries]):
    """Repository for workspace-scoped entries.

    Validates entry content (data_json) against entry type schema (schema_json)
    when creating or updating entries.
    """

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Entries,
            schema=EntryRead,
            group_id=group_id,
        )
        self.content_validator = ContentValidator()

    def _get_base_query(self):
        """Override to eagerly load collections, assets (with junction data), and resources relationships."""
        query = super()._get_base_query()
        return query.options(
            joinedload(Entries.collections),
            joinedload(Entries.entry_assets).joinedload(EntryAssets.asset),
            joinedload(Entries.entry_resources).joinedload(EntryResources.resource),
        )

    def _entry_type_exists(self, entry_type_id: UUID4) -> bool:
        """Check if entry type exists (includes system types)."""
        from sqlalchemy import or_

        query = select(EntryTypes.id).filter_by(id=entry_type_id)
        if self.group_id:
            # Include both workspace types AND system types
            query = query.filter(
                or_(
                    EntryTypes.group_id == self.group_id,
                    EntryTypes.group_id.is_(None),
                )
            )
        else:
            query = query.filter(EntryTypes.group_id.is_(None))
        return self.session.scalar(query) is not None

    def _get_entry_type(self, entry_type_id: UUID4) -> EntryTypes | None:
        """Get entry type by ID.

        Includes both workspace-scoped types AND system types (group_id=NULL).

        Args:
            entry_type_id: Entry type UUID

        Returns:
            EntryTypes model or None if not found
        """
        from sqlalchemy import or_

        query = select(EntryTypes).filter_by(id=entry_type_id)
        if self.group_id:
            # Include both workspace types AND system types
            query = query.filter(
                or_(
                    EntryTypes.group_id == self.group_id,
                    EntryTypes.group_id.is_(None),
                )
            )
        else:
            # If no group_id, only system types
            query = query.filter(EntryTypes.group_id.is_(None))
        return self.session.scalar(query)

    def _validate_content(self, entry_type_id: UUID4, data_json: dict) -> None:
        """Validate entry content against entry type schema.

        Args:
            entry_type_id: Entry type UUID
            data_json: Entry content data to validate

        Raises:
            HTTPException: If validation fails
        """
        # Get entry type with schema
        entry_type = self._get_entry_type(entry_type_id)
        if not entry_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entry type does not exist in this group.",
            )

        # Skip validation if no schema defined (legacy/default behavior)
        if not entry_type.schema_json or not entry_type.schema_json.get("fields"):
            return

        # Parse schema definition
        try:
            schema_def = EntryTypeSchemaDefinition.model_validate(entry_type.schema_json)
        except Exception as e:
            # Schema is invalid - this shouldn't happen if entry type was validated on create
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Entry type has invalid schema: {e}",
            )

        # Validate content against schema
        try:
            self.content_validator.validate_content(schema_def, data_json)
        except ContentValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content validation failed: {e.message}",
            )

    def create(self, data: Any) -> EntryRead:
        from datetime import datetime, timezone
        from slugify import slugify

        data_dict = data if isinstance(data, dict) else data.model_dump()
        if self.group_id:
            data_dict["group_id"] = self.group_id

        # Auto-generate slug from title if not provided
        if not data_dict.get("slug") and data_dict.get("title"):
            data_dict["slug"] = slugify(data_dict["title"])

        # Validate entry type exists
        if not self._entry_type_exists(data_dict["entry_type_id"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entry type does not exist in this group.",
            )

        # Validate content against entry type schema
        if "data_json" in data_dict:
            self._validate_content(data_dict["entry_type_id"], data_dict["data_json"])

        # Auto-set published_at when creating with status 'published'
        if data_dict.get("status") == "published" and not data_dict.get("published_at"):
            data_dict["published_at"] = datetime.now(timezone.utc)

        # Extract relationship IDs before creating entry
        collection_ids = data_dict.pop("collection_ids", None)
        asset_ids = data_dict.pop("asset_ids", None)
        resource_ids = data_dict.pop("resource_ids", None)
        asset_attachments = data_dict.pop("asset_attachments", None)
        resource_attachments = data_dict.pop("resource_attachments", None)

        new_entry = self.model(session=self.session, **data_dict)
        self.session.add(new_entry)
        self.session.flush()

        if collection_ids:
            self._attach_collections(new_entry.id, collection_ids)
        if asset_attachments:
            self._attach_asset_attachments(new_entry.id, asset_attachments)
        elif asset_ids:
            self._attach_assets(new_entry.id, asset_ids)
        if resource_attachments:
            self._attach_resource_attachments(new_entry.id, resource_attachments)
        elif resource_ids:
            self._attach_resources(new_entry.id, resource_ids)

        self.session.commit()

        return self.get_one(new_entry.id)

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> EntryRead:
        from datetime import datetime, timezone
        from slugify import slugify

        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)

        # Get existing entry to check publish status
        existing_entry = self.get_one(match_value, key=match_key)

        # Slug handling based on publish status
        if existing_entry.status == "published":
            # Published entries: slug is immutable to protect external URLs/SEO
            data_dict.pop("slug", None)
        else:
            # Unpublished entries: allow manual slug override, otherwise auto-generate from title
            if "slug" not in data_dict or not data_dict.get("slug"):
                # No manual slug provided - auto-generate if title is changing
                if "title" in data_dict and data_dict.get("title"):
                    data_dict["slug"] = slugify(data_dict["title"])
            # else: user provided explicit slug, use it as-is

        # Handle published_at based on status changes
        if "status" in data_dict:
            print(f"\n{'='*80}")
            print(f"DEBUG: Status change detected: {data_dict['status']}")
            if data_dict["status"] == "published":
                # Only set published_at if not already provided (first publish)
                if "published_at" not in data_dict:
                    # Get current entry to check if it was already published
                    current_entry = self.get_one(match_value, key=match_key)
                    print(f"Current entry published_at: {current_entry.published_at if current_entry else 'None'}")
                    if current_entry and not current_entry.published_at:
                        new_timestamp = datetime.now(timezone.utc)
                        data_dict["published_at"] = new_timestamp
                        print(f"Setting published_at to: {new_timestamp}")
                    else:
                        print(f"Not setting published_at (already has value or entry not found)")
                else:
                    print(f"published_at already in data_dict: {data_dict['published_at']}")
            else:
                # If unpublishing (changing to draft/etc), clear published_at
                data_dict["published_at"] = None
                print(f"Clearing published_at (status changed to {data_dict['status']})")
            print(f"{'='*80}\n")

        # Validate entry type exists if being changed
        entry_type_id = data_dict.get("entry_type_id")
        if entry_type_id and not self._entry_type_exists(entry_type_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entry type does not exist in this group.",
            )

        # Validate content if being updated
        # Need to determine which entry_type_id to use (new or existing)
        if "data_json" in data_dict:
            # Get the entry to find its entry_type_id if not being changed
            if not entry_type_id:
                existing_entry = self.get_one(match_value, key=match_key or self.primary_key)
                if existing_entry:
                    entry_type_id = existing_entry.entry_type_id

            if entry_type_id:
                self._validate_content(entry_type_id, data_dict["data_json"])

        data_dict.pop("group_id", None)

        # Extract relationship IDs before updating entry
        collection_ids = data_dict.pop("collection_ids", None)
        asset_ids = data_dict.pop("asset_ids", None)
        resource_ids = data_dict.pop("resource_ids", None)
        asset_attachments = data_dict.pop("asset_attachments", None)
        resource_attachments = data_dict.pop("resource_attachments", None)

        # Update the entry
        entry = super().update(match_value, data_dict, match_key=match_key)

        has_rel_changes = False

        # Update relationships if provided (replace existing)
        if collection_ids is not None:
            self._replace_collections(entry.id, collection_ids)
            has_rel_changes = True
        if asset_attachments is not None:
            self._replace_asset_attachments(entry.id, asset_attachments)
            has_rel_changes = True
        elif asset_ids is not None:
            self._replace_assets(entry.id, asset_ids)
            has_rel_changes = True
        if resource_attachments is not None:
            self._replace_resource_attachments(entry.id, resource_attachments)
            has_rel_changes = True
        elif resource_ids is not None:
            self._replace_resources(entry.id, resource_ids)
            has_rel_changes = True

        if has_rel_changes:
            self.session.commit()
            self.session.refresh(self.session.get(Entries, entry.id))
            entry = self.get_one(entry.id)

        return entry

    def _attach_collections(self, entry_id: UUID4, collection_ids: list[UUID4]) -> None:
        """Attach collections to an entry."""
        for sort_order, collection_id in enumerate(collection_ids):
            junction = EntryCollections(entry_id=entry_id, collection_id=collection_id, sort_order=sort_order)
            self.session.add(junction)
        self.session.flush()

    def _attach_assets(self, entry_id: UUID4, asset_ids: list[UUID4]) -> None:
        """Attach assets to an entry."""
        for position, asset_id in enumerate(asset_ids):
            junction = EntryAssets(entry_id=entry_id, asset_id=asset_id, position=position)
            self.session.add(junction)
        self.session.flush()

    def _attach_resources(self, entry_id: UUID4, resource_ids: list[UUID4]) -> None:
        """Attach resources to an entry."""
        for position, resource_id in enumerate(resource_ids):
            junction = EntryResources(entry_id=entry_id, resource_id=resource_id, position=position)
            self.session.add(junction)
        self.session.flush()

    def _replace_collections(self, entry_id: UUID4, collection_ids: list[UUID4]) -> None:
        """Replace all collections for an entry."""
        # Delete existing
        self.session.query(EntryCollections).filter(EntryCollections.entry_id == entry_id).delete()
        # Add new
        if collection_ids:
            self._attach_collections(entry_id, collection_ids)

    def _replace_assets(self, entry_id: UUID4, asset_ids: list[UUID4]) -> None:
        """Replace all assets for an entry."""
        # Delete existing
        self.session.query(EntryAssets).filter(EntryAssets.entry_id == entry_id).delete()
        # Add new
        if asset_ids:
            self._attach_assets(entry_id, asset_ids)

    def _replace_resources(self, entry_id: UUID4, resource_ids: list[UUID4]) -> None:
        """Replace all resources for an entry."""
        # Delete existing
        self.session.query(EntryResources).filter(EntryResources.entry_id == entry_id).delete()
        # Add new
        if resource_ids:
            self._attach_resources(entry_id, resource_ids)

    def _attach_asset_attachments(self, entry_id: UUID4, attachments: list) -> None:
        """Attach assets with rich placement data."""
        for idx, att in enumerate(attachments):
            att_dict = att if isinstance(att, dict) else att.model_dump()
            junction = EntryAssets(
                entry_id=entry_id,
                asset_id=att_dict["asset_id"],
                position=att_dict.get("position") if att_dict.get("position") is not None else idx,
                role=att_dict.get("role"),
                caption=att_dict.get("caption"),
                focal_point=att_dict.get("focal_point"),
                metadata_json=att_dict.get("metadata"),
            )
            self.session.add(junction)
        self.session.flush()

    def _attach_resource_attachments(self, entry_id: UUID4, attachments: list) -> None:
        """Attach resources with rich placement data."""
        for idx, att in enumerate(attachments):
            att_dict = att if isinstance(att, dict) else att.model_dump()
            junction = EntryResources(
                entry_id=entry_id,
                resource_id=att_dict["resource_id"],
                position=att_dict.get("position") if att_dict.get("position") is not None else idx,
                role=att_dict.get("role"),
                quantity=att_dict.get("quantity"),
                unit=att_dict.get("unit"),
                metadata_json=att_dict.get("metadata"),
            )
            self.session.add(junction)
        self.session.flush()

    def _replace_asset_attachments(self, entry_id: UUID4, attachments: list) -> None:
        """Replace all asset attachments for an entry."""
        self.session.query(EntryAssets).filter(EntryAssets.entry_id == entry_id).delete()
        if attachments:
            self._attach_asset_attachments(entry_id, attachments)

    def _replace_resource_attachments(self, entry_id: UUID4, attachments: list) -> None:
        """Replace all resource attachments for an entry."""
        self.session.query(EntryResources).filter(EntryResources.entry_id == entry_id).delete()
        if attachments:
            self._attach_resource_attachments(entry_id, attachments)
