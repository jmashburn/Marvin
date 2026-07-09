"""Entry repositories."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from marvin.db.models.platform import Entries, EntryTypes, EntryCollections, EntryAssets, EntryResources
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import EntryRead


class EntriesRepository(GroupRepositoryGeneric[EntryRead, Entries]):
    """Repository for workspace-scoped entries."""

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Entries,
            schema=EntryRead,
            group_id=group_id,
        )

    def _get_base_query(self):
        """Override to eagerly load collections, assets (with junction data), and resources relationships."""
        query = super()._get_base_query()
        return query.options(
            joinedload(Entries.collections),
            joinedload(Entries.entry_assets).joinedload(EntryAssets.asset),  # Load junction + asset details
            joinedload(Entries.resources),
        )

    def _entry_type_exists(self, entry_type_id: UUID4) -> bool:
        query = select(EntryTypes.id).filter_by(id=entry_type_id)
        if self.group_id:
            query = query.filter_by(group_id=self.group_id)
        return self.session.scalar(query) is not None

    def create(self, data: Any) -> EntryRead:
        from datetime import datetime, timezone
        from slugify import slugify

        data_dict = data if isinstance(data, dict) else data.model_dump()
        if self.group_id:
            data_dict["group_id"] = self.group_id

        # Auto-generate slug from title if not provided
        if not data_dict.get("slug") and data_dict.get("title"):
            data_dict["slug"] = slugify(data_dict["title"])

        # Auto-set published_at when creating with status 'published'
        if data_dict.get("status") == "published" and not data_dict.get("published_at"):
            data_dict["published_at"] = datetime.now(timezone.utc)

        if not self._entry_type_exists(data_dict["entry_type_id"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entry type does not exist in this group.")

        # Extract relationship IDs before creating entry
        collection_ids = data_dict.pop("collection_ids", None)
        asset_ids = data_dict.pop("asset_ids", None)
        resource_ids = data_dict.pop("resource_ids", None)

        # Create entry model instance but don't commit yet
        new_entry = self.model(session=self.session, **data_dict)
        self.session.add(new_entry)
        self.session.flush()  # Flush to get the entry ID

        # Attach relationships if provided
        if collection_ids:
            self._attach_collections(new_entry.id, collection_ids)
        if asset_ids:
            self._attach_assets(new_entry.id, asset_ids)
        if resource_ids:
            self._attach_resources(new_entry.id, resource_ids)

        # Now commit everything together
        self.session.commit()

        # Return via get_one to get all relationships loaded
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

        entry_type_id = data_dict.get("entry_type_id")
        if entry_type_id and not self._entry_type_exists(entry_type_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entry type does not exist in this group.")
        data_dict.pop("group_id", None)

        # Extract relationship IDs before updating entry
        collection_ids = data_dict.pop("collection_ids", None)
        asset_ids = data_dict.pop("asset_ids", None)
        resource_ids = data_dict.pop("resource_ids", None)

        # Update the entry
        entry = super().update(match_value, data_dict, match_key=match_key)

        # Update relationships if provided (replace existing)
        if collection_ids is not None:
            self._replace_collections(entry.id, collection_ids)
        if asset_ids is not None:
            self._replace_assets(entry.id, asset_ids)
        if resource_ids is not None:
            self._replace_resources(entry.id, resource_ids)

        # Commit the relationship changes
        if collection_ids is not None or asset_ids is not None or resource_ids is not None:
            self.session.commit()

        # Refresh to get updated relationships
        if collection_ids is not None or asset_ids is not None or resource_ids is not None:
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
