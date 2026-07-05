"""Site Client schemas."""

from typing import Annotated

from pydantic import ConfigDict, StringConstraints, UUID4

from marvin.schemas._marvin import _MarvinModel


class SiteClientCreate(_MarvinModel):
    """Schema for creating a new site client."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """Name of the site client."""
    slug: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    """URL-friendly slug for the site client."""
    permissions: list[str]
    """List of permissions (e.g., 'read:published_entries', 'read:collections')."""

    model_config = ConfigDict(from_attributes=True)


class SiteClientUpdate(_MarvinModel):
    """Schema for updating a site client."""

    id: UUID4
    """The unique identifier of the site client to update."""
    name: str | None = None
    """New name for the site client."""
    permissions: list[str] | None = None
    """Updated permissions list."""
    is_active: bool | None = None
    """Whether the site client is active."""

    model_config = ConfigDict(from_attributes=True)


class SiteClientSummary(_MarvinModel):
    """Summary schema for a site client."""

    id: UUID4
    """Unique identifier."""
    name: str
    """Name of the site client."""
    slug: str
    """URL-friendly slug."""
    is_active: bool
    """Whether the site client is active."""

    model_config = ConfigDict(from_attributes=True)


class SiteClientRead(SiteClientSummary):
    """Full schema for reading a site client."""

    permissions: list[str]
    """List of permissions."""
    last_used_at: str | None = None
    """When the token was last used."""
    created_by: UUID4
    """ID of user who created the site client."""
    revoked_at: str | None = None
    """When the site client was revoked."""

    model_config = ConfigDict(from_attributes=True)
