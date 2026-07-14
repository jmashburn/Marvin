"""Entry schemas."""

from datetime import datetime
from typing import Annotated, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, StringConstraints, UUID4, field_validator, field_serializer, model_validator, Field, AliasChoices

from marvin.schemas._marvin import _MarvinModel

if TYPE_CHECKING:
    from .assets import EntryAssetRead
    from .collections import EntryCollectionRead
    from .resources import EntryResourceRead

ENTRY_STATUSES = {
    "inbox",
    "processing",
    "draft",
    "needs_review",
    "approved",
    "published",
    "archived",
}


class AssetAttachment(BaseModel):
    asset_id: UUID4
    role: str | None = None
    position: int | None = None
    metadata: dict | None = None


class ResourceAttachment(BaseModel):
    resource_id: UUID4
    role: str | None = None
    position: int | None = None
    metadata: dict | None = None


class CollectionAttachment(BaseModel):
    collection_id: UUID4
    role: str | None = None
    metadata: dict | None = None


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
    collection_attachments: list[CollectionAttachment] | None = None
    asset_ids: list[UUID4] | None = None
    resource_ids: list[UUID4] | None = None
    asset_attachments: list[AssetAttachment] | None = None
    resource_attachments: list[ResourceAttachment] | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ENTRY_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(ENTRY_STATUSES))}")
        return value

    @model_validator(mode="after")
    def check_no_ambiguous_attachments(self):
        if self.asset_ids and self.asset_attachments:
            raise ValueError("Provide asset_ids or asset_attachments, not both")
        if self.resource_ids and self.resource_attachments:
            raise ValueError("Provide resource_ids or resource_attachments, not both")
        if self.collection_ids and self.collection_attachments:
            raise ValueError("Provide collection_ids or collection_attachments, not both")
        return self

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
    collection_attachments: list[CollectionAttachment] | None = Field(
        default=None, validation_alias=AliasChoices("collection_attachments", "collectionAttachments")
    )
    asset_ids: list[UUID4] | None = Field(default=None, validation_alias=AliasChoices("asset_ids", "assetIds"))
    resource_ids: list[UUID4] | None = Field(default=None, validation_alias=AliasChoices("resource_ids", "resourceIds"))
    asset_attachments: list[AssetAttachment] | None = Field(default=None, validation_alias=AliasChoices("asset_attachments", "assetAttachments"))
    resource_attachments: list[ResourceAttachment] | None = Field(
        default=None, validation_alias=AliasChoices("resource_attachments", "resourceAttachments")
    )

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

    @model_validator(mode="after")
    def check_no_ambiguous_attachments(self):
        if self.asset_ids and self.asset_attachments:
            raise ValueError("Provide asset_ids or asset_attachments, not both")
        if self.resource_ids and self.resource_attachments:
            raise ValueError("Provide resource_ids or resource_attachments, not both")
        if self.collection_ids and self.collection_attachments:
            raise ValueError("Provide collection_ids or collection_attachments, not both")
        return self

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
    resources: list["EntryResourceRead"] = []
    """Resources referenced by this entry with placement info."""
    assets: list["EntryAssetRead"] = []
    """Assets included in this entry with placement info."""
    collections: list["EntryCollectionRead"] = []
    """Collections this entry belongs to, with placement info."""
    order: int | None = None
    """Sort order within a collection. Only populated when querying entries for a specific collection."""

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to extract collection IDs and build asset/resource details."""
        data = {field: getattr(obj, field, None) for field in cls.model_fields}

        if hasattr(obj, "collections") and obj.collections:
            if obj.collections and hasattr(obj.collections[0], "id"):
                data["collections"] = [c.id for c in obj.collections]

        if hasattr(obj, "entry_collections") and obj.entry_collections:
            from marvin.schemas.platform.collections import EntryCollectionRead

            collections = []
            for junction in obj.entry_collections:
                if hasattr(junction, "collection") and junction.collection:
                    c = junction.collection
                    collections.append(
                        EntryCollectionRead(
                            id=c.id,
                            name=c.name,
                            slug=c.slug,
                            icon=c.icon,
                            color=c.color,
                            role=junction.role,
                            placement_metadata=junction.metadata_json,
                            sort_order=junction.sort_order,
                        )
                    )
            data["collections"] = collections

            if obj.entry_collections and hasattr(obj.entry_collections[0], "sort_order"):
                data["order"] = obj.entry_collections[0].sort_order

        if hasattr(obj, "entry_assets") and obj.entry_assets:
            from marvin.schemas.platform.assets import EntryAssetRead

            assets = []
            for junction in obj.entry_assets:
                if hasattr(junction, "asset") and junction.asset:
                    asset_data = {
                        **{k: getattr(junction.asset, k, None) for k in EntryAssetRead.model_fields if hasattr(junction.asset, k)},
                        "role": junction.role,
                        "position": junction.position,
                        "placement_metadata": junction.metadata_json,
                    }
                    assets.append(asset_data)
            data["assets"] = assets

        if hasattr(obj, "entry_resources") and obj.entry_resources:
            from marvin.schemas.platform.resources import EntryResourceRead

            resources = []
            for junction in obj.entry_resources:
                if hasattr(junction, "resource") and junction.resource:
                    resource_data = {
                        **{k: getattr(junction.resource, k, None) for k in EntryResourceRead.model_fields if hasattr(junction.resource, k)},
                        "role": junction.role,
                        "position": junction.position,
                        "placement_metadata": junction.metadata_json,
                    }
                    resources.append(resource_data)
            data["resources"] = resources

        return super().model_validate(data, **kwargs)


class EntrySummary(EntryRead):
    """Summary schema for an entry."""

    pass
