"""Entry type repository."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import UUID4, ValidationError
from sqlalchemy.orm import Session

from marvin.db.models.platform import Entries, EntryTypes
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import EntryTypeRead
from marvin.schemas.platform.entry_type_schema import EntryTypeSchemaDefinition


class EntryTypesRepository(GroupRepositoryGeneric[EntryTypeRead, EntryTypes]):
    """Repository for workspace-scoped entry types.

    Validates schema_json against EntryTypeSchemaDefinition when creating/updating.
    """

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=EntryTypes,
            schema=EntryTypeRead,
            group_id=group_id,
        )

    def _validate_schema_json(self, schema_json: dict | None) -> None:
        """Validate schema_json against EntryTypeSchemaDefinition.

        Args:
            schema_json: The schema definition to validate

        Raises:
            HTTPException: If schema validation fails
        """
        if schema_json is None:
            return

        try:
            EntryTypeSchemaDefinition.model_validate(schema_json)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid schema definition: {e}",
            )

    def create(self, data: Any) -> EntryTypeRead:
        from slugify import slugify

        data_dict = data if isinstance(data, dict) else data.model_dump()

        # DEBUG: Log what we received
        print(f"[DEBUG] create() received data_dict keys: {data_dict.keys()}")
        print(f"[DEBUG] content_schema in data_dict: {'content_schema' in data_dict}")
        print(f"[DEBUG] schema_json in data_dict: {'schema_json' in data_dict}")
        if "content_schema" in data_dict:
            print(f"[DEBUG] content_schema value: {data_dict['content_schema']}")
        if "schema_json" in data_dict:
            print(f"[DEBUG] schema_json value: {data_dict['schema_json']}")

        if self.group_id:
            data_dict["group_id"] = self.group_id

        # Auto-generate slug from name if not provided
        if not data_dict.get("slug") and data_dict.get("name"):
            data_dict["slug"] = slugify(data_dict["name"])

        # Map content_schema to schema_json (Pydantic field name to DB column name)
        if "content_schema" in data_dict:
            data_dict["schema_json"] = data_dict.pop("content_schema")
            print(f"[DEBUG] After mapping, schema_json value: {data_dict['schema_json']}")

        # Validate schema_json if provided
        if "schema_json" in data_dict:
            print(f"[DEBUG] Validating schema_json: {data_dict['schema_json']}")
            self._validate_schema_json(data_dict["schema_json"])

        print(f"[DEBUG] Final data_dict before super().create(): {data_dict}")
        return super().create(data_dict)

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> EntryTypeRead:
        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)

        # Auto-regenerate slug if name is being updated
        if "name" in data_dict and data_dict.get("name"):
            data_dict["slug"] = slugify(data_dict["name"])

        # Map content_schema to schema_json (Pydantic field name to DB column name)
        if "content_schema" in data_dict:
            data_dict["schema_json"] = data_dict.pop("content_schema")

        # Validate schema_json if provided
        if "schema_json" in data_dict:
            self._validate_schema_json(data_dict["schema_json"])

        # Don't auto-regenerate slug on update - slugs should remain stable once created
        # to avoid breaking references in entries and external integrations
        data_dict.pop("slug", None)
        data_dict.pop("group_id", None)
        return super().update(match_value, data_dict, match_key=match_key)

    def delete(self, value: Any, match_key: str | None = None) -> EntryTypeRead:
        entry_count = self._count_attribute("entry_type_id", value)
        if entry_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Entry type is in use by entries and cannot be deleted.",
            )
        return super().delete(value, match_key=match_key)

    def _count_attribute(self, attribute_name: str, attr_match: Any | None = None) -> int:
        count_query = self.session.query(Entries).filter(getattr(Entries, attribute_name) == attr_match)
        if self.group_id:
            count_query = count_query.filter(Entries.group_id == self.group_id)
        return count_query.count()
