"""Resource schemas."""

from typing import Annotated, Any

from pydantic import AliasChoices, ConfigDict, Field, StringConstraints, UUID4, field_validator

from marvin.schemas._marvin import _MarvinModel


class ResourceCreate(_MarvinModel):
    """Schema for creating a new resource."""

    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """URL-friendly slug for the resource."""
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """Name of the resource."""
    resource_type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """Type of resource (fabric, tool, supplier, etc)."""
    description: str | None = None
    """Optional description of the resource."""
    url: str | None = None
    """External URL (supplier site, GitHub repo, API docs, etc)."""
    external_id: str | None = None
    """External identifier (supplier SKU, ISBN, repo path, etc)."""
    metadata_json: dict | None = Field(default=None, validation_alias=AliasChoices("metadata", "metadata_json"))
    """Optional metadata as JSON."""

    model_config = ConfigDict(from_attributes=True)


class ResourceUpdate(_MarvinModel):
    """Schema for updating a resource."""

    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    """URL-friendly slug for the resource."""
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    """Name of the resource."""
    resource_type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    """Type of resource (fabric, tool, supplier, etc)."""
    description: str | None = None
    """Optional description of the resource."""
    url: str | None = None
    """External URL (supplier site, GitHub repo, API docs, etc)."""
    external_id: str | None = None
    """External identifier (supplier SKU, ISBN, repo path, etc)."""
    metadata_json: dict | None = Field(default=None, validation_alias=AliasChoices("metadata", "metadata_json"))
    """Optional metadata for additional properties."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ResourceSummary(_MarvinModel):
    """Summary schema for a resource."""

    id: UUID4
    """Unique identifier."""
    slug: str
    """URL-friendly slug."""
    name: str
    """Name of the resource."""
    resource_type: str
    """Type of resource."""
    description: str | None = None
    """Optional description."""
    url: str | None = None
    """External URL."""
    external_id: str | None = None
    """External identifier."""

    model_config = ConfigDict(from_attributes=True)


class ResourceRead(ResourceSummary):
    """Full schema for reading a resource."""

    metadata_json: dict | None = None
    """Optional metadata."""
    created_by: UUID4
    """ID of user who created the resource."""

    model_config = ConfigDict(from_attributes=True)


class ResourcePlacement(_MarvinModel):
    """How a resource is used by a specific entry."""

    role: str | None = None
    position: int = 0
    placement_metadata: dict | None = Field(
        default=None,
        validation_alias=AliasChoices("placement_metadata", "metadata_json"),
    )

    @field_validator("placement_metadata", mode="before")
    @classmethod
    def validate_placement_metadata(cls, value: Any) -> dict | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            return None
        return value

    model_config = ConfigDict(from_attributes=True)


class EntryResourceRead(ResourceSummary, ResourcePlacement):
    """Resource metadata plus entry-specific placement details."""

    model_config = ConfigDict(from_attributes=True)
