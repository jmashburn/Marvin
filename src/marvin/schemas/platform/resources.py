"""Resource schemas."""

from typing import Annotated

from pydantic import AliasChoices, ConfigDict, Field, StringConstraints, UUID4

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
    metadata: dict | None = Field(default=None, validation_alias=AliasChoices("metadata", "metadata_"))
    """Optional metadata as JSON."""

    model_config = ConfigDict(from_attributes=True)


class ResourceUpdate(ResourceCreate):
    """Schema for updating a resource."""

    id: UUID4
    """The unique identifier of the resource to update."""


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

    model_config = ConfigDict(from_attributes=True)


class ResourceRead(ResourceSummary):
    """Full schema for reading a resource."""

    metadata: dict | None = Field(default=None, validation_alias=AliasChoices("metadata", "metadata_"))
    """Optional metadata."""
    created_by: UUID4
    """ID of user who created the resource."""

    model_config = ConfigDict(from_attributes=True)
