"""Collections repository."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform import Collections, EntryCollections
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import CollectionRead


class CollectionsRepository(GroupRepositoryGeneric[CollectionRead, Collections]):
    """Repository for managing collections."""

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Collections,
            schema=CollectionRead,
            group_id=group_id,
        )

    def create(self, data: Any) -> CollectionRead:
        from slugify import slugify

        data_dict = data if isinstance(data, dict) else data.model_dump()
        if self.group_id:
            data_dict["group_id"] = self.group_id

        # Auto-generate slug from name if not provided
        if not data_dict.get("slug") and data_dict.get("name"):
            data_dict["slug"] = slugify(data_dict["name"])

        # Extract entry_ids before creating collection
        entry_ids = data_dict.pop("entry_ids", None)

        # Create collection model instance but don't commit yet
        new_collection = self.model(session=self.session, **data_dict)
        self.session.add(new_collection)
        self.session.flush()  # Flush to get the collection ID

        # Attach entries if provided
        if entry_ids:
            self._attach_entries(new_collection.id, entry_ids)

        # Now commit everything together
        self.session.commit()

        # Return via get_one to get all relationships loaded
        return self.get_one(new_collection.id)

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> CollectionRead:
        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)

        # Don't auto-regenerate slug on update - slugs should remain stable once created
        # to avoid breaking references in Publishing API, external integrations, and bookmarks
        data_dict.pop("slug", None)
        data_dict.pop("group_id", None)

        # Extract entry_ids before updating collection
        entry_ids = data_dict.pop("entry_ids", None)

        # Update the collection
        collection = super().update(match_value, data_dict, match_key=match_key)

        # Replace entries if provided
        if entry_ids is not None:
            self._replace_entries(collection.id, entry_ids)
            # Refresh to get updated relationships
            self.session.refresh(self.session.get(Collections, collection.id))
            collection = self.get_one(collection.id)

        return collection

    def delete(self, value: Any, match_key: str | None = None) -> CollectionRead:
        entry_count = self._count_entries_in_collection(value)
        if entry_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Collection is in use by entries and cannot be deleted.",
            )
        return super().delete(value, match_key=match_key)

    def _count_entries_in_collection(self, collection_id: Any) -> int:
        count_query = self.session.query(EntryCollections).filter(EntryCollections.collection_id == collection_id)
        return count_query.count()

    def _attach_entries(self, collection_id: UUID4, entry_ids: list[UUID4]) -> None:
        """Attach entries to a collection."""
        for position, entry_id in enumerate(entry_ids):
            junction = EntryCollections(entry_id=entry_id, collection_id=collection_id, position=position)
            self.session.add(junction)
        self.session.flush()

    def _replace_entries(self, collection_id: UUID4, entry_ids: list[UUID4]) -> None:
        """Replace all entries in a collection."""
        # Delete existing
        self.session.query(EntryCollections).filter(EntryCollections.collection_id == collection_id).delete()
        # Add new
        if entry_ids:
            self._attach_entries(collection_id, entry_ids)
