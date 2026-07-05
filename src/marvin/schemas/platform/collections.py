"""Collection schemas."""

from typing import Annotated

from pydantic import ConfigDict, StringConstraints, UUID4

from marvin.schemas._marvin import _MarvinModel


class CollectionCreate(_MarvinModel):
    """Schema for creating a new collection."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """Name of the collection."""
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """URL-friendly slug for the collection."""
    description: str | None = None
    """Optional description of the collection."""
    is_smart: bool = False
    """Whether this is a smart collection based on rules."""
    smart_rules: dict | None = None
    """Optional rules for smart collections."""

    model_config = ConfigDict(from_attributes=True)


class CollectionUpdate(CollectionCreate):
    """Schema for updating a collection."""

    id: UUID4
    """The unique identifier of the collection to update."""


class CollectionSummary(_MarvinModel):
    """Summary schema for a collection."""

    id: UUID4
    """Unique identifier."""
    name: str
    """Name of the collection."""
    slug: str
    """URL-friendly slug."""
    description: str | None = None
    """Optional description."""
    is_smart: bool
    """Whether this is a smart collection."""

    model_config = ConfigDict(from_attributes=True)


class CollectionRead(CollectionSummary):
    """Full schema for reading a collection."""

    entry_count: int | None = None
    """Number of entries in the collection."""

    model_config = ConfigDict(from_attributes=True)
