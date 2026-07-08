"""Entry schemas."""

from datetime import datetime
from typing import Annotated, TYPE_CHECKING

from pydantic import ConfigDict, StringConstraints, UUID4, field_validator, field_serializer

from marvin.schemas._marvin import _MarvinModel

if TYPE_CHECKING:
    from .assets import EntryAssetRead
    from .resources import ResourceSummary

ENTRY_STATUSES = {
    "inbox",
    "processing",
    "draft",
    "needs_review",
    "approved",
    "published",
    "archived",
}


class EntryCreate(_MarvinModel):
    """Schema for creating an entry."""

    entry_type_id: UUID4
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    summary: str | None = None
    description: str | None = None
    content_markdown: str | None = None
    status: str = "inbox"
    published_at: datetime | None = None
    metadata_json: dict | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ENTRY_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(ENTRY_STATUSES))}")
        return value

    model_config = ConfigDict(from_attributes=True)


class EntryUpdate(_MarvinModel):
    """Schema for patching an entry."""

    entry_type_id: UUID4 | None = None
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    summary: str | None = None
    description: str | None = None
    content_markdown: str | None = None
    status: str | None = None
    published_at: datetime | None = None
    metadata_json: dict | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in ENTRY_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(ENTRY_STATUSES))}")
        return value

    @field_validator("published_at", mode="before")
    @classmethod
    def validate_published_at(cls, value: str | datetime | None) -> datetime | None:
        """Convert empty strings to None for published_at."""
        if value == "":
            return None
        return value

    model_config = ConfigDict(from_attributes=True)


class EntryRead(_MarvinModel):
    """Schema for reading an entry."""

    id: UUID4
    group_id: UUID4
    entry_type_id: UUID4
    title: str
    slug: str
    summary: str | None = None
    description: str | None = None
    content_markdown: str | None = None
    status: str
    published_at: datetime | None = None
    metadata_json: dict | None = None
    """Custom metadata fields for this entry."""
    created_by: UUID4 | None = None
    created_at: datetime | None = None
    update_at: datetime | None = None
    resources: list["ResourceSummary"] = []
    """Resources referenced by this entry."""
    assets: list["EntryAssetRead"] = []
    """Assets included in this entry with placement info."""
    collections: list[UUID4] = []
    """Collection IDs this entry belongs to."""

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to extract collection IDs from collection objects."""
        if hasattr(obj, "collections") and obj.collections:
            # If collections are Collection objects, extract their IDs
            if obj.collections and hasattr(obj.collections[0], "id"):
                collection_ids = [c.id for c in obj.collections]
                # Create a dict with all attributes
                data = {field: getattr(obj, field, None) for field in cls.model_fields}
                data["collections"] = collection_ids
                return super().model_validate(data, **kwargs)
        return super().model_validate(obj, **kwargs)


class EntrySummary(EntryRead):
    """Summary schema for an entry."""

    pass
