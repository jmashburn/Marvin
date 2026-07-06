"""Entry repositories."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session

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

    def _entry_type_exists(self, entry_type_id: UUID4) -> bool:
        query = select(EntryTypes.id).filter_by(id=entry_type_id)
        if self.group_id:
            query = query.filter_by(group_id=self.group_id)
        return self.session.scalar(query) is not None

    def create(self, data: Any) -> EntryRead:
        from slugify import slugify

        data_dict = data if isinstance(data, dict) else data.model_dump()
        if self.group_id:
            data_dict["group_id"] = self.group_id

        # Auto-generate slug from title if not provided
        if not data_dict.get("slug") and data_dict.get("title"):
            data_dict["slug"] = slugify(data_dict["title"])

        if not self._entry_type_exists(data_dict["entry_type_id"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entry type does not exist in this group.")
        return super().create(data_dict)

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> EntryRead:
        from slugify import slugify

        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)

        # Auto-regenerate slug if title is being updated
        if "title" in data_dict and data_dict.get("title"):
            data_dict["slug"] = slugify(data_dict["title"])

        entry_type_id = data_dict.get("entry_type_id")
        if entry_type_id and not self._entry_type_exists(entry_type_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entry type does not exist in this group.")
        data_dict.pop("group_id", None)
        return super().update(match_value, data_dict, match_key=match_key)
