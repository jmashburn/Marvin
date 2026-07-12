"""Entry type schemas."""

from datetime import datetime
from typing import Annotated

from pydantic import AliasChoices, ConfigDict, Field, StringConstraints, UUID4, field_validator
from pydantic_core.core_schema import ValidationInfo

from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.platform.entry_type_rendering import CapabilitiesDefinition, RenderingDefinition
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
    is_rendered: bool = False
    content_schema: dict | None = Field(
        default=None,
        description="Entry type schema definition (EntryTypeSchemaDefinition)",
        serialization_alias="schemaJson",
        validation_alias=AliasChoices("schema_json", "schemaJson"),
    )
    rendering: dict | None = Field(
        default=None,
        description="Rendering configuration (RenderingDefinition)",
        serialization_alias="renderingJson",
        validation_alias=AliasChoices("rendering_json", "renderingJson"),
    )
    capabilities: dict | None = Field(
        default=None,
        description="Behavioral capabilities (CapabilitiesDefinition)",
        serialization_alias="capabilitiesJson",
        validation_alias=AliasChoices("capabilities_json", "capabilitiesJson"),
    )

    @field_validator("content_schema")
    @classmethod
    def validate_content_schema(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        EntryTypeSchemaDefinition.model_validate(value)
        return value

    @field_validator("rendering")
    @classmethod
    def validate_rendering(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        RenderingDefinition.model_validate(value)
        return value

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        CapabilitiesDefinition.model_validate(value)
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
    is_rendered: bool | None = None
    content_schema: dict | None = Field(
        default=None,
        description="Entry type schema definition (EntryTypeSchemaDefinition)",
        serialization_alias="schemaJson",
        validation_alias=AliasChoices("schema_json", "schemaJson"),
    )
    rendering: dict | None = Field(
        default=None,
        description="Rendering configuration (RenderingDefinition)",
        serialization_alias="renderingJson",
        validation_alias=AliasChoices("rendering_json", "renderingJson"),
    )
    capabilities: dict | None = Field(
        default=None,
        description="Behavioral capabilities (CapabilitiesDefinition)",
        serialization_alias="capabilitiesJson",
        validation_alias=AliasChoices("capabilities_json", "capabilitiesJson"),
    )

    @field_validator("content_schema")
    @classmethod
    def validate_content_schema(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        EntryTypeSchemaDefinition.model_validate(value)
        return value

    @field_validator("rendering")
    @classmethod
    def validate_rendering(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        RenderingDefinition.model_validate(value)
        return value

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        CapabilitiesDefinition.model_validate(value)
        return value

    model_config = ConfigDict(from_attributes=True)


class EntryTypeRead(_MarvinModel):
    """Schema for reading an entry type.

    System entry types have group_id=None and are globally available to all workspaces.
    Workspace-scoped entry types have a specific group_id.
    """

    id: UUID4
    group_id: UUID4 | None
    name: str
    slug: str
    icon: str | None = None
    color: str | None = None
    description: str | None = None
    sort_order: int
    is_system: bool
    is_rendered: bool = False
    content_schema: dict | None = Field(
        default=None,
        description="Entry type schema definition (EntryTypeSchemaDefinition)",
        serialization_alias="schemaJson",
        validation_alias=AliasChoices("schema_json", "schemaJson"),
    )
    rendering: dict | None = Field(
        default=None,
        description="Rendering configuration (RenderingDefinition)",
        serialization_alias="renderingJson",
        validation_alias=AliasChoices("rendering_json", "renderingJson"),
    )
    capabilities: dict | None = Field(
        default=None,
        description="Behavioral capabilities (CapabilitiesDefinition)",
        serialization_alias="capabilitiesJson",
        validation_alias=AliasChoices("capabilities_json", "capabilitiesJson"),
    )
    created_at: datetime | None = None
    update_at: datetime | None = None
    warnings: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class EntryTypeSummary(EntryTypeRead):
    """Summary schema for an entry type."""

    pass
