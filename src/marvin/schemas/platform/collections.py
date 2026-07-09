"""Collection schemas."""

from datetime import datetime
from typing import Annotated

from pydantic import ConfigDict, StringConstraints, UUID4

from marvin.schemas._marvin import _MarvinModel


class CollectionCreate(_MarvinModel):
    """Schema for creating a new collection."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """Name of the collection."""
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    """URL-friendly slug for the collection. Auto-generated from name if not provided."""
    description: str | None = None
    """Optional description of the collection."""
    sort_order: int = 0
    """Display order for UI (lower numbers first)."""
    icon: str | None = None
    """Optional icon identifier for UI display."""
    color: str | None = None
    """Optional color code for UI display (e.g., '#FF5733')."""
    is_smart: bool = False
    """Whether this is a smart collection based on rules."""
    smart_rules: dict | None = None
    """Optional rules for smart collections."""
    metadata_json: dict | None = None
    """Custom metadata for this collection."""
    entry_ids: list[UUID4] | None = None
    """Optional list of entry IDs to add to this collection."""

    model_config = ConfigDict(from_attributes=True)


class CollectionUpdate(_MarvinModel):
    """Schema for updating a collection."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    """Name of the collection."""
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    """URL-friendly slug for the collection."""
    description: str | None = None
    """Optional description of the collection."""
    sort_order: int | None = None
    """Display order for UI."""
    icon: str | None = None
    """Optional icon identifier."""
    color: str | None = None
    """Optional color code."""
    is_smart: bool | None = None
    """Whether this is a smart collection based on rules."""
    smart_rules: dict | None = None
    """Optional rules for smart collections."""
    metadata_json: dict | None = None
    """Custom metadata for this collection."""
    entry_ids: list[UUID4] | None = None
    """Optional list of entry IDs to replace existing entries in this collection."""

    model_config = ConfigDict(from_attributes=True)


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
    sort_order: int
    """Display order."""
    icon: str | None = None
    """Optional icon identifier."""
    color: str | None = None
    """Optional color code."""
    is_smart: bool
    """Whether this is a smart collection."""
    created_at: datetime | None = None
    """Timestamp when the collection was created."""
    update_at: datetime | None = None
    """Timestamp when the collection was last updated."""

    model_config = ConfigDict(from_attributes=True)


class CollectionRead(CollectionSummary):
    """Full schema for reading a collection."""

    group_id: UUID4
    """The workspace/group this collection belongs to."""
    smart_rules: dict | None = None
    """Optional rules for smart collections."""
    metadata_json: dict | None = None
    """Custom metadata for this collection."""

    model_config = ConfigDict(from_attributes=True)
