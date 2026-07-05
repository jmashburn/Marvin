"""Asset schemas."""

from typing import Annotated, Any

from pydantic import UUID4, AliasChoices, ConfigDict, Field, StringConstraints, field_serializer, field_validator

from marvin.schemas._marvin import _MarvinModel


class AssetCreate(_MarvinModel):
    """Schema for creating a new asset."""

    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """URL-friendly slug for the asset."""
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """Name of the asset."""
    file_path: Annotated[str, StringConstraints(min_length=1)]
    """Path to the file in storage."""
    file_size: int
    """Size of the file in bytes."""
    mime_type: str
    """MIME type of the file."""
    width: int | None = None
    """Width in pixels (for images)."""
    height: int | None = None
    """Height in pixels (for images)."""
    alt_text: str | None = None
    """Alt text for accessibility."""
    description: str | None = None
    """Optional description of the asset."""
    metadata_: dict | None = Field(default=None, validation_alias=AliasChoices("metadata", "metadata_"))
    """Optional asset metadata."""

    model_config = ConfigDict(from_attributes=True)


class AssetSummary(_MarvinModel):
    """Summary schema for an asset."""

    id: UUID4
    """Unique identifier."""
    slug: str
    """URL-friendly slug."""
    name: str
    """Name of the asset."""
    mime_type: str
    """MIME type of the file."""
    alt_text: str | None = None
    """Alt text for accessibility."""

    model_config = ConfigDict(from_attributes=True)


class AssetRead(AssetSummary):
    """Full schema for reading an asset."""

    file_size: int
    """Size of the file in bytes."""
    width: int | None = None
    """Width in pixels."""
    height: int | None = None
    """Height in pixels."""
    description: str | None = None
    """Optional description."""
    metadata_: dict | None = Field(default=None, validation_alias=AliasChoices("metadata_"))
    """Optional asset metadata."""
    uploaded_by: UUID4
    """ID of user who uploaded the asset."""

    @field_validator('metadata_', mode='before')
    @classmethod
    def validate_metadata(cls, value: Any) -> dict | None:
        """Ensure metadata is a dict, not SQLAlchemy MetaData."""
        if value is None:
            return None
        # If it's a SQLAlchemy MetaData object, return None instead
        if hasattr(value, '__class__') and value.__class__.__name__ == 'MetaData':
            return None
        # If it's not a dict, try to convert or return None
        if not isinstance(value, dict):
            return None
        return value

    @field_serializer('metadata_')
    def serialize_metadata(self, value: dict | None, _info) -> dict | None:
        """Ensure metadata is serialized as dict."""
        return value if isinstance(value, dict) else None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AssetPlacement(_MarvinModel):
    """How an asset is used by a specific entry."""

    role: str | None = None
    """Role for this entry, such as hero, featured, support, inline, or download."""
    usage: str | None = None
    """Usage hint, such as material, process, detail, texture, or workshop."""
    position: int = 0
    """Display order for this entry."""
    focal_point: str | None = None
    """CSS-style focal point for cropped media, such as '50% 50%'."""
    caption: str | None = None
    """Optional caption for this placement."""
    placement_metadata: dict | None = Field(
        default=None,
        validation_alias=AliasChoices("placement_metadata", "metadata", "metadata_"),
    )
    """Optional placement metadata."""

    model_config = ConfigDict(from_attributes=True)


class EntryAssetRead(AssetRead, AssetPlacement):
    """Asset metadata plus entry-specific placement details."""

    model_config = ConfigDict(from_attributes=True)
