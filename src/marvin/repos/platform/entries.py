"""Entry repositories."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from marvin.db.models.platform import Entries, EntryTypes
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
        """Override to eagerly load collections, assets, and resources relationships."""
        query = super()._get_base_query()
        return query.options(joinedload(Entries.collections), joinedload(Entries.assets), joinedload(Entries.resources))

    def _entry_type_exists(self, entry_type_id: UUID4) -> bool:
        query = select(EntryTypes.id).filter_by(id=entry_type_id)
        if self.group_id:
            query = query.filter_by(group_id=self.group_id)
        return self.session.scalar(query) is not None

    def _get_entry_type(self, entry_type_id: UUID4) -> EntryTypes | None:
        """Get entry type by ID.

        Args:
            entry_type_id: Entry type UUID

        Returns:
            EntryTypes model or None if not found
        """
        query = select(EntryTypes).filter_by(id=entry_type_id)
        if self.group_id:
            query = query.filter_by(group_id=self.group_id)
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

        return super().create(data_dict)

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> EntryRead:
        from slugify import slugify

        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)

        # Auto-regenerate slug if title is being updated
        if "title" in data_dict and data_dict.get("title"):
            data_dict["slug"] = slugify(data_dict["title"])

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
                existing_entry = self.get_one(match_value, match_key=match_key or self.primary_key)
                if existing_entry:
                    entry_type_id = existing_entry.entry_type_id

            if entry_type_id:
                self._validate_content(entry_type_id, data_dict["data_json"])

        data_dict.pop("group_id", None)
        return super().update(match_value, data_dict, match_key=match_key)
