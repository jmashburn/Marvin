"""Entry repositories."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from marvin.db.models.platform import Entries, EntryTypes
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
        """Override to eagerly load collections, assets, and resources relationships."""
        query = super()._get_base_query()
        return query.options(joinedload(Entries.collections), joinedload(Entries.assets), joinedload(Entries.resources))

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
        return super().create(data_dict)

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> EntryRead:
        from datetime import datetime, timezone
        from slugify import slugify

        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)

        # Auto-regenerate slug if title is being updated
        if "title" in data_dict and data_dict.get("title"):
            data_dict["slug"] = slugify(data_dict["title"])

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
        return super().update(match_value, data_dict, match_key=match_key)
