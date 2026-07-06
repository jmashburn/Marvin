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

        return super().create(data_dict)

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> CollectionRead:
        from slugify import slugify

        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)

        # Auto-regenerate slug if name is being updated
        if "name" in data_dict and data_dict.get("name"):
            data_dict["slug"] = slugify(data_dict["name"])

        data_dict.pop("group_id", None)
        return super().update(match_value, data_dict, match_key=match_key)

    def delete(self, value: Any, match_key: str | None = None) -> CollectionRead:
        entry_count = self._count_entries_in_collection(value)
        if entry_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Collection is in use by entries and cannot be deleted.",
            )
        return super().delete(value, match_key=match_key)

    def _count_entries_in_collection(self, collection_id: Any) -> int:
        count_query = self.session.query(EntryCollections).filter(
            EntryCollections.collection_id == collection_id
        )
        return count_query.count()
