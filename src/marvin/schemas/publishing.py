"""
Publishing API schemas.

These schemas are used for the public-facing publishing API and exclude
all admin fields, internal metadata, and unpublished content.
"""

from datetime import datetime

from pydantic import UUID4, ConfigDict, Field

from marvin.schemas._marvin import _MarvinModel


class PublishedAssetRead(_MarvinModel):
    """
    Schema for published assets in the publishing API.

    Provides asset metadata for external sites to build proper media tags.
    Read-only, does not expose internal fields like storage_key or uploaded_by.
    """

    slug: str
    """URL-friendly identifier for the asset."""

    name: str
    """Asset name/title."""

    mime_type: str
    """MIME type of the file (e.g., 'image/jpeg', 'application/pdf')."""

    asset_type: str
    """Asset type classification (image, document, video, audio, archive, svg, other)."""

    file_size: int
    """File size in bytes."""

    width: int | None = None
    """Width in pixels (for images)."""

    height: int | None = None
    """Height in pixels (for images)."""

    alt_text: str | None = None
    """Alt text for accessibility."""

    description: str | None = None
    """Optional description of the asset."""

    public_url: str
    """Public URL to access the asset file."""

    metadata: dict | None = Field(default=None, serialization_alias="metadataJson")
    """Custom metadata as JSON object."""

    model_config = ConfigDict(from_attributes=True)


class PublishedEntryRead(_MarvinModel):
    """
    Schema for published entries in the publishing API.

    Only includes public-facing fields. Excludes all admin metadata,
    internal fields, and user information.

    BREAKING CHANGE: content_markdown removed, replaced with data.
    Entry content is now schema-driven based on entry_type.schema_json.
    """

    slug: str
    """URL-friendly identifier for the entry."""

    title: str
    """Entry title."""

    entry_type: str
    """Entry type slug (e.g., 'page', 'article', 'project')."""

    summary: str | None = None
    """Optional short description/summary."""

    data: dict
    """Entry content structured according to entry type schema."""

    published_at: datetime | None = None
    """Timestamp when the entry was published."""

    metadata: dict | None = Field(default=None, serialization_alias="metadataJson")
    """Custom non-schema metadata as JSON object."""

    collections: list["PublishedCollectionSummary"] = []
    """Collections this entry belongs to."""

    resources: list["PublishedResourceRead"] = []
    """Resources referenced by this entry."""

    assets: list[PublishedAssetRead] = []
    """Assets included in this entry."""

    order: int | None = None
    """Sort order within a collection. Only populated when querying entries for a specific collection."""

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

    status: str
    """Entry status (e.g., 'published', 'draft', 'needs_review')."""

    collections: list[str] = []
    """List of collection slugs this entry belongs to."""

    assets: list[str] = Field(default=[], serialization_alias="assetSlugs")
    """List of asset slugs included in this entry."""

    resources: list[str] = Field(default=[], serialization_alias="resourceSlugs")
    """List of resource slugs referenced by this entry."""

    order: int | None = None
    """Sort order within a collection. Only populated when querying entries for a specific collection."""

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(_MarvinModel):
    """Pagination metadata."""

    total: int
    """Total number of items available."""

    page: int
    """Current page number (1-indexed)."""

    limit: int
    """Number of items per page."""

    offset: int
    """Offset for pagination."""


class PublishedEntriesResponse(_MarvinModel):
    """
    Paginated response for listing published entries.
    """

    data: list[PublishedEntryListItem]
    """List of published entries."""

    meta: PaginationMeta
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

    is_smart: bool = False
    """Whether this is a smart collection with automatic rules."""

    smart_rules: dict | None = None
    """Smart collection rules (JSON object)."""

    metadata: dict | None = Field(default=None, serialization_alias="metadataJson")
    """Custom metadata as JSON object."""

    entry_count: int
    """Number of published entries in this collection."""

    entries: list[PublishedEntryListItem]
    """Published entries in this collection."""

    model_config = ConfigDict(from_attributes=True)


class PublishedCollectionSummary(_MarvinModel):
    """
    Summary schema for published collections (for listing).

    Minimal collection info for entry contexts - only includes
    essential fields for display and ordering.
    """

    slug: str
    """URL-friendly identifier for the collection."""

    name: str
    """Collection display name."""

    metadata: dict | None = Field(default=None, serialization_alias="metadataJson")
    """Custom metadata as JSON object."""

    sort_order: int
    """Display order for UI."""

    model_config = ConfigDict(from_attributes=True)


class PublishedResourceSummary(_MarvinModel):
    """
    Schema for published resources in standalone context.

    Provides resource metadata without entry-specific placement info.
    Used for listing resources and getting individual resource details.
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

    metadata: dict | None = Field(default=None, serialization_alias="metadataJson")
    """Custom metadata as JSON object."""

    entries: list[str] = []
    """List of entry slugs that reference this resource."""

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

    metadata: dict | None = Field(default=None, serialization_alias="metadataJson")
    """Custom metadata as JSON object."""

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

    metadata: dict | None = Field(default=None, serialization_alias="metadataJson")
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


class PublishedCollectionsResponse(_MarvinModel):
    """
    Paginated response for listing published collections.
    """

    data: list[PublishedCollectionSummary]
    """List of published collections."""

    meta: PaginationMeta
    """Pagination metadata."""

    model_config = ConfigDict(from_attributes=True)


class PublishedResourcesResponse(_MarvinModel):
    """
    Paginated response for listing published resources.
    """

    data: list[PublishedResourceSummary]
    """List of published resources."""

    meta: PaginationMeta
    """Pagination metadata."""

    model_config = ConfigDict(from_attributes=True)


class PublishedAssetsResponse(_MarvinModel):
    """
    Paginated response for listing published assets.
    """

    data: list[PublishedAssetRead]
    """List of published assets."""

    meta: PaginationMeta
    """Pagination metadata."""

    model_config = ConfigDict(from_attributes=True)


class PublishedFormRead(_MarvinModel):
    """
    Schema for published forms in the publishing API.

    Provides form definition for frontend to render the form.
    Does not expose internal fields like submissions_count.
    """

    slug: str
    """URL-friendly identifier for the form."""

    name: str
    """Form display name."""

    description: str | None = None
    """Optional description of the form."""

    form_schema: dict
    """Form field definitions."""

    metadata: dict | None = None
    """Custom metadata (if publicly exposed)."""

    model_config = ConfigDict(from_attributes=True)


class FormSubmissionResponse(_MarvinModel):
    """
    Response after form submission.

    Indicates success/failure and optionally provides redirect URL.
    """

    success: bool
    """Whether submission was successful."""

    message: str
    """User-facing message."""

    submission_id: UUID4 | None = None
    """Submission ID (if persisted)."""

    redirect_url: str | None = None
    """Optional redirect URL."""

    model_config = ConfigDict(from_attributes=True)
