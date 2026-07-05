"""
Publishing API schemas.

These schemas are used for the public-facing publishing API and exclude
all admin fields, internal metadata, and unpublished content.
"""

from datetime import datetime

from pydantic import UUID4, ConfigDict

from marvin.schemas._marvin import _MarvinModel


class PublishedAssetRead(_MarvinModel):
    """
    Schema for published assets in the publishing API.

    Provides asset metadata for external sites to build proper media tags.
    """

    slug: str
    """URL-friendly identifier for the asset."""

    name: str
    """Asset name/title."""

    mime_type: str
    """MIME type of the file (e.g., 'image/jpeg', 'application/pdf')."""

    width: int | None = None
    """Width in pixels (for images)."""

    height: int | None = None
    """Height in pixels (for images)."""

    alt_text: str | None = None
    """Alt text for accessibility."""

    file_url: str
    """URL to download the asset file."""

    model_config = ConfigDict(from_attributes=True)


class PublishedEntryRead(_MarvinModel):
    """
    Schema for published entries in the publishing API.

    Only includes public-facing fields. Excludes all admin metadata,
    internal fields, and user information.
    """

    slug: str
    """URL-friendly identifier for the entry."""

    title: str
    """Entry title."""

    entry_type: str
    """Entry type slug (e.g., 'page', 'article', 'project')."""

    summary: str | None = None
    """Optional short description/summary."""

    content_markdown: str | None = None
    """Full entry content in Markdown format."""

    published_at: datetime | None = None
    """Timestamp when the entry was published."""

    metadata: dict | None = None
    """Custom frontmatter/metadata as JSON object."""

    collections: list[str] = []
    """List of collection slugs this entry belongs to."""

    resources: list["PublishedResourceRead"] = []
    """Resources referenced by this entry."""

    assets: list[PublishedAssetRead] = []
    """Assets included in this entry."""

    model_config = ConfigDict(from_attributes=True)


class PublishedEntryListItem(_MarvinModel):
    """
    Minimal entry schema for list responses.

    Used when listing multiple entries - returns only essential fields
    without full content.
    """

    slug: str
    """URL-friendly identifier for the entry."""

    title: str
    """Entry title."""

    entry_type: str
    """Entry type slug (e.g., 'page', 'article', 'project')."""

    summary: str | None = None
    """Optional short description/summary."""

    published_at: datetime | None = None
    """Timestamp when the entry was published."""

    collections: list[str] = []
    """List of collection slugs this entry belongs to."""

    model_config = ConfigDict(from_attributes=True)


class PublishedEntriesResponse(_MarvinModel):
    """
    Paginated response for listing published entries.
    """

    data: list[PublishedEntryListItem]
    """List of published entries."""

    meta: dict
    """Pagination metadata (total, page, limit)."""

    model_config = ConfigDict(from_attributes=True)


class PublishedCollectionRead(_MarvinModel):
    """
    Schema for published collections in the publishing API.

    Includes collection metadata and its published entries.
    """

    slug: str
    """URL-friendly identifier for the collection."""

    name: str
    """Collection display name."""

    description: str | None = None
    """Optional collection description."""

    entry_count: int
    """Number of published entries in this collection."""

    entries: list[PublishedEntryListItem]
    """Published entries in this collection."""

    model_config = ConfigDict(from_attributes=True)


class PublishedCollectionSummary(_MarvinModel):
    """
    Summary schema for published collections (for listing).
    """

    slug: str
    """URL-friendly identifier for the collection."""

    name: str
    """Collection display name."""

    description: str | None = None
    """Optional collection description."""

    entry_count: int
    """Number of published entries in this collection."""

    sort_order: int
    """Display order for UI."""

    icon: str | None = None
    """Optional icon identifier."""

    color: str | None = None
    """Optional color code."""

    model_config = ConfigDict(from_attributes=True)


class PublishedResourceRead(_MarvinModel):
    """
    Schema for published resources in entry context.

    Combines resource metadata with entry-specific placement info.
    """

    slug: str
    """URL-friendly identifier for the resource."""

    name: str
    """Resource name."""

    resource_type: str
    """Type of resource (fabric, tool, supplier, etc)."""

    description: str | None = None
    """Optional description."""

    url: str | None = None
    """External URL (supplier site, GitHub repo, etc)."""

    external_id: str | None = None
    """External identifier (SKU, ISBN, etc)."""

    # Entry-specific placement fields from junction table
    role: str | None = None
    """Role in this entry (e.g., 'primary', 'alternative')."""

    quantity: str | None = None
    """Quantity for this entry (e.g., '2 yards')."""

    unit: str | None = None
    """Unit of measurement (e.g., 'meters', 'pieces')."""

    position: int = 0
    """Display order in this entry."""

    model_config = ConfigDict(from_attributes=True)


class WorkspaceInfo(_MarvinModel):
    """
    Public workspace information for publishing API.
    """

    slug: str
    """Workspace slug."""

    name: str
    """Workspace name."""

    model_config = ConfigDict(from_attributes=True)


class SiteConfiguration(_MarvinModel):
    """
    Site configuration for publishing API.

    Provides the public identity and settings for a workspace's published site.
    This replaces hardcoded site.ts files in Astro projects.
    """

    title: str | None = None
    """The public title of the site."""

    tagline: str | None = None
    """A short tagline or slogan."""

    description: str | None = None
    """Site description."""

    canonical_url: str | None = None
    """The canonical URL where this site is published."""

    logo: str | None = None
    """Path or URL to the site logo."""

    favicon: str | None = None
    """Path or URL to the site favicon."""

    locale: str = "en-US"
    """Site locale (e.g., en-US, en-GB)."""

    timezone: str = "America/New_York"
    """Site timezone (e.g., America/New_York)."""

    contact_email: str | None = None
    """Primary contact email."""

    social: dict | None = None
    """Social media links (e.g., {instagram: 'url', facebook: 'url'})."""

    metadata: dict | None = None
    """Framework-specific or custom site metadata."""

    model_config = ConfigDict(from_attributes=True)


class WorkspaceSiteInfo(_MarvinModel):
    """
    Combined workspace and site configuration response.

    Returns everything an external site needs to initialize itself.
    """

    workspace: WorkspaceInfo
    """Workspace identification."""

    site: SiteConfiguration
    """Site configuration and identity."""

    model_config = ConfigDict(from_attributes=True)
