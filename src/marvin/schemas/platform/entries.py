"""Entry schemas."""

from datetime import datetime
from typing import Annotated, TYPE_CHECKING

from pydantic import ConfigDict, StringConstraints, UUID4, field_validator, field_serializer, Field, AliasChoices

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
    """Schema for creating an entry.

    BREAKING CHANGE: content_markdown removed, replaced with data_json.
    Entry content is now schema-driven based on entry_type.schema_json.
    """

    entry_type_id: UUID4
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    summary: str | None = None
    description: str | None = None
    data_json: dict = Field(
        default_factory=dict,
        description="Schema-driven content data (validated against entry_type.schema_json)",
        serialization_alias="dataJson",
    )
    status: str = "inbox"
    published_at: datetime | None = None
    publish_at: datetime | None = None
    expire_at: datetime | None = None
    metadata_json: dict | None = Field(
        default=None,
        description="Custom non-schema metadata (API keys, external IDs, etc.)",
        serialization_alias="metadataJson",
    )
    collection_ids: list[UUID4] | None = None
    asset_ids: list[UUID4] | None = None
    resource_ids: list[UUID4] | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ENTRY_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(ENTRY_STATUSES))}")
        return value

    model_config = ConfigDict(from_attributes=True)


class EntryUpdate(_MarvinModel):
    """Schema for patching an entry.

    BREAKING CHANGE: content_markdown removed, replaced with data_json.
    Entry content is now schema-driven based on entry_type.schema_json.
    """

    entry_type_id: UUID4 | None = Field(default=None, validation_alias=AliasChoices("entry_type_id", "entryTypeId"))
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    summary: str | None = None
    description: str | None = None
    data_json: dict | None = Field(
        default=None,
        description="Schema-driven content data (validated against entry_type.schema_json)",
        serialization_alias="dataJson",
    )
    status: str | None = None
    published_at: datetime | None = None
    publish_at: datetime | None = None
    expire_at: datetime | None = None
    metadata_json: dict | None = Field(
        default=None,
        description="Custom non-schema metadata (API keys, external IDs, etc.)",
        serialization_alias="metadataJson",
    )
    collection_ids: list[UUID4] | None = Field(default=None, validation_alias=AliasChoices("collection_ids", "collectionIds"))
    asset_ids: list[UUID4] | None = Field(default=None, validation_alias=AliasChoices("asset_ids", "assetIds"))
    resource_ids: list[UUID4] | None = Field(default=None, validation_alias=AliasChoices("resource_ids", "resourceIds"))

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in ENTRY_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(ENTRY_STATUSES))}")
        return value

    @field_validator("published_at", "publish_at", "expire_at", mode="before")
    @classmethod
    def validate_datetime_fields(cls, value: str | datetime | None) -> datetime | None:
        """Convert empty strings to None for datetime fields."""
        if value == "":
            return None
        return value

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EntryRead(_MarvinModel):
    """Schema for reading an entry.

    BREAKING CHANGE: content_markdown removed, replaced with data_json.
    Entry content is now schema-driven based on entry_type.schema_json.
    """

    id: UUID4
    group_id: UUID4
    entry_type_id: UUID4
    title: str
    slug: str
    summary: str | None = None
    description: str | None = None
    data_json: dict = Field(
        default_factory=dict,
        description="Schema-driven content data",
        serialization_alias="dataJson",
    )
    status: str
    published_at: datetime | None = None
    publish_at: datetime | None = None
    expire_at: datetime | None = None
    metadata_json: dict | None = Field(
        default=None,
        description="Custom non-schema metadata",
        serialization_alias="metadataJson",
    )
    created_by: UUID4 | None = None
    created_at: datetime | None = None
    update_at: datetime | None = None
    resources: list["ResourceSummary"] = []
    """Resources referenced by this entry."""
    assets: list["EntryAssetRead"] = []
    """Assets included in this entry with placement info."""
    collections: list[UUID4] = []
    """Collection IDs this entry belongs to."""
    order: int | None = None
    """Sort order within a collection. Only populated when querying entries for a specific collection."""

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
        """Custom validation to extract collection IDs and build asset/resource details."""
        data = {field: getattr(obj, field, None) for field in cls.model_fields}

        # Extract collection IDs from collection objects
        if hasattr(obj, "collections") and obj.collections:
            if obj.collections and hasattr(obj.collections[0], "id"):
                data["collections"] = [c.id for c in obj.collections]

        # Extract order from entry_collections junction table if querying for a specific collection
        if hasattr(obj, "entry_collections") and obj.entry_collections:
            # Use the first junction's sort_order (typically only one when filtering by collection)
            if obj.entry_collections and hasattr(obj.entry_collections[0], "sort_order"):
                data["order"] = obj.entry_collections[0].sort_order

        # Build assets from entry_assets junction table (includes placement metadata)
        if hasattr(obj, "entry_assets") and obj.entry_assets:
            from marvin.schemas.platform.assets import EntryAssetRead

            assets = []
            for junction in obj.entry_assets:
                if hasattr(junction, "asset") and junction.asset:
                    # Combine asset data + junction placement data
                    asset_data = {
                        # Asset fields
                        **{k: getattr(junction.asset, k, None) for k in EntryAssetRead.model_fields if hasattr(junction.asset, k)},
                        # Placement fields from junction
                        "role": junction.role,
                        "usage": junction.usage,
                        "position": junction.position,
                        "focal_point": junction.focal_point,
                        "caption": junction.caption,
                        "placement_metadata": junction.metadata_,
                    }
                    assets.append(asset_data)
            data["assets"] = assets

        return super().model_validate(data, **kwargs)


class EntrySummary(EntryRead):
    """Summary schema for an entry."""

    pass
