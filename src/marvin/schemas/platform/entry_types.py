"""Entry type schemas."""

from datetime import datetime
from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints, UUID4, field_validator
from pydantic_core.core_schema import ValidationInfo

from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.platform.entry_type_schema import EntryTypeSchemaDefinition


class EntryTypeCreate(_MarvinModel):
    """Schema for creating an entry type."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    icon: str | None = None
    color: str | None = None
    description: str | None = None
    sort_order: int = 0
    is_system: bool = False
    schema_json: dict | None = Field(
        default=None,
        description="Entry type schema definition (EntryTypeSchemaDefinition)",
        serialization_alias="schemaJson",
    )

    @field_validator("schema_json")
    @classmethod
    def validate_schema_json(cls, value: dict | None) -> dict | None:
        """Validate schema_json against EntryTypeSchemaDefinition."""
        if value is None:
            return None

        # Validate against EntryTypeSchemaDefinition
        # This will raise ValidationError if invalid
        EntryTypeSchemaDefinition.model_validate(value)
        return value

    model_config = ConfigDict(from_attributes=True)


class EntryTypeUpdate(_MarvinModel):
    """Schema for patching an entry type."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    icon: str | None = None
    color: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_system: bool | None = None
    schema_json: dict | None = Field(
        default=None,
        description="Entry type schema definition (EntryTypeSchemaDefinition)",
        serialization_alias="schemaJson",
    )

    @field_validator("schema_json")
    @classmethod
    def validate_schema_json(cls, value: dict | None) -> dict | None:
        """Validate schema_json against EntryTypeSchemaDefinition."""
        if value is None:
            return None

        # Validate against EntryTypeSchemaDefinition
        EntryTypeSchemaDefinition.model_validate(value)
        return value

    model_config = ConfigDict(from_attributes=True)


class EntryTypeRead(_MarvinModel):
    """Schema for reading an entry type."""

    id: UUID4
    group_id: UUID4
    name: str
    slug: str
    icon: str | None = None
    color: str | None = None
    description: str | None = None
    sort_order: int
    is_system: bool
    schema_json: dict = Field(
        default_factory=dict,
        description="Entry type schema definition (EntryTypeSchemaDefinition)",
        serialization_alias="schemaJson",
    )
    created_at: datetime | None = None
    update_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EntryTypeSummary(EntryTypeRead):
    """Summary schema for an entry type."""

    pass
