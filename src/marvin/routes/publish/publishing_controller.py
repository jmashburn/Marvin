"""
Publishing API controller.

Provides read-only access to published content for external sites (Astro, etc.).
All routes require API client token authentication (marvin_sk_ prefix).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from marvin.core.config import get_app_settings
from marvin.core.dependencies import get_publishing_context
from marvin.core.permissions import Permissions
from marvin.db.db_setup import generate_session
from marvin.db.models.platform import APIClients, Assets, Collections, Entries, Resources
from marvin.repos.all_repositories import get_repositories
from marvin.schemas.group import GroupRead
from marvin.schemas.publishing import (
    PaginationMeta,
    PublishedAssetRead,
    PublishedAssetsResponse,
    PublishedCollectionRead,
    PublishedCollectionsResponse,
    PublishedCollectionSummary,
    PublishedEntriesResponse,
    PublishedEntryListItem,
    PublishedEntryRead,
    PublishedResourceRead,
    PublishedResourcesResponse,
    PublishedResourceSummary,
    SiteConfiguration,
    WorkspaceInfo,
    WorkspaceSiteInfo,
)

settings = get_app_settings()

router = APIRouter()


@router.get("/{workspace_slug}", response_model=WorkspaceInfo, summary="Get Workspace Info")
async def get_workspace_info(
    context: tuple = Depends(get_publishing_context),
) -> WorkspaceInfo:
    """
    Get public workspace information.

    Returns basic workspace metadata for site consumption.

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:published_entries (minimal permission to access publishing API)
    """
    api_client, group, perms = context

    # Require at least one publishing permission to access workspace info
    perms.require_any_permission([Permissions.READ_PUBLISHED_ENTRIES, Permissions.READ_ALL_ENTRIES], "workspace information")

    return WorkspaceInfo(
        slug=group.slug,
        name=group.name,
    )


@router.get("/{workspace_slug}/site", response_model=WorkspaceSiteInfo, summary="Get Site Configuration")
async def get_site_configuration(
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> WorkspaceSiteInfo:
    """
    Get workspace and site configuration.

    Returns complete site identity and settings for external sites (Astro, etc.).
    This replaces hardcoded site.ts files - all site configuration lives in Marvin.

    **Response includes:**
    - Workspace identity (name, slug)
    - Site settings (title, tagline, description, URLs)
    - Contact information
    - Social media links
    - Localization settings
    - Custom metadata

    **Use case**: Astro site initialization, meta tags, social links, contact forms.

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:published_entries (minimal permission to access publishing API)
    """
    api_client, group, perms = context

    # Require at least one publishing permission to access site configuration
    perms.require_any_permission([Permissions.READ_PUBLISHED_ENTRIES, Permissions.READ_ALL_ENTRIES], "site configuration")

    # Get group preferences (includes site configuration)
    from marvin.db.models.groups import GroupPreferencesModel

    prefs = session.query(GroupPreferencesModel).filter(GroupPreferencesModel.group_id == group.id).first()

    # Build site configuration from preferences (with sensible defaults)
    site_config = SiteConfiguration(
        title=prefs.site_title if prefs and prefs.site_title else group.name,
        tagline=prefs.site_tagline if prefs else None,
        description=prefs.site_description if prefs else None,
        canonical_url=prefs.site_canonical_url if prefs else None,
        logo=prefs.site_logo if prefs else None,
        favicon=prefs.site_favicon if prefs else None,
        locale=prefs.site_locale if prefs and prefs.site_locale else "en-US",
        timezone=prefs.site_timezone if prefs and prefs.site_timezone else "America/New_York",
        contact_email=prefs.site_contact_email if prefs else None,
        social=prefs.site_social_json if prefs else None,
        metadata=prefs.site_metadata_json if prefs else None,
    )

    return WorkspaceSiteInfo(
        workspace=WorkspaceInfo(
            slug=group.slug,
            name=group.name,
        ),
        site=site_config,
    )


@router.get(
    "/{workspace_slug}/entries",
    response_model=PublishedEntriesResponse,
    summary="List Published Entries",
)
async def list_published_entries(
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
    entry_type: str | None = Query(None, description="Filter by entry type slug"),
    collection: str | None = Query(None, description="Filter by collection slug"),
    slug: str | None = Query(None, description="Filter by specific slug(s), comma-separated"),
    updated_since: str | None = Query(None, description="Filter by entries updated since ISO datetime"),
    limit: int = Query(settings.PUBLISHING_DEFAULT_PAGE_SIZE, ge=1, le=settings.PUBLISHING_MAX_PAGE_SIZE, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> PublishedEntriesResponse:
    """
    List all published entries in the workspace.

    Supports filtering by entry type, collection, slug, and updated date, plus pagination.

    **Filters:**
    - Only returns entries with `status = 'published'`
    - Scoped to the workspace associated with the API client
    - `entry_type`: Filter by entry type slug
    - `collection`: Filter by collection slug
    - `slug`: Filter by specific slug(s), comma-separated for batch fetching
    - `updated_since`: ISO datetime, returns entries updated after this time

    **Use cases:**
    - `?entry_type=page` - Get all static pages
    - `?collection=projects` - Get all project entries
    - `?slug=about,contact,sizing` - Batch fetch specific pages
    - `?updated_since=2026-07-01T00:00:00Z` - Incremental builds

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:published_entries OR read:all_entries
    """
    api_client, group, perms = context

    # Require permission to read entries
    perms.require_any_permission([Permissions.READ_PUBLISHED_ENTRIES, Permissions.READ_ALL_ENTRIES], "published entries")

    # Get repositories scoped to this workspace
    repos = get_repositories(session, group_id=group.id)

    # Build query for published entries
    query = session.query(Entries).filter(
        Entries.group_id == group.id,
        Entries.status == settings.PUBLISHING_DEFAULT_STATUS,
    )

    # Filter by entry type if specified
    if entry_type:
        from marvin.db.models.platform import EntryTypes

        entry_type_obj = session.query(EntryTypes).filter(EntryTypes.group_id == group.id, EntryTypes.slug == entry_type).first()

        if not entry_type_obj:
            # Return empty list if entry type doesn't exist
            return PublishedEntriesResponse(
                data=[],
                meta=PaginationMeta(
                    total=0,
                    page=(offset // limit) + 1,
                    limit=limit,
                    offset=offset,
                ),
            )

        query = query.filter(Entries.entry_type_id == entry_type_obj.id)

    # Filter by collection if specified
    if collection:
        from marvin.db.models.platform import EntryCollections

        # Get collection
        collection_obj = session.query(Collections).filter(Collections.group_id == group.id, Collections.slug == collection).first()

        if not collection_obj:
            # Return empty list if collection doesn't exist
            return PublishedEntriesResponse(
                data=[],
                meta=PaginationMeta(
                    total=0,
                    page=(offset // limit) + 1,
                    limit=limit,
                    offset=offset,
                ),
            )

        # Join with entry_collections to filter
        query = query.join(EntryCollections).filter(EntryCollections.collection_id == collection_obj.id)

    # Filter by slug(s) if specified
    if slug:
        slugs = [s.strip() for s in slug.split(",")]
        query = query.filter(Entries.slug.in_(slugs))

    # Filter by updated_since if specified
    if updated_since:
        from datetime import datetime

        try:
            updated_dt = datetime.fromisoformat(updated_since.replace("Z", "+00:00"))
            query = query.filter(Entries.update_at >= updated_dt)
        except ValueError:
            # Invalid datetime format, ignore filter
            pass

    # Get total count
    total = query.count()

    # Apply pagination
    entries = query.order_by(Entries.published_at.desc()).offset(offset).limit(limit).all()

    # Convert to list items
    data = []
    for entry in entries:
        # Get collection slugs
        collection_slugs = [ec.collection.slug for ec in entry.entry_collections if ec.collection]

        # Get asset slugs
        asset_slugs = [ea.asset.slug for ea in entry.entry_assets if ea.asset]

        # Get resource slugs
        resource_slugs = [er.resource.slug for er in entry.entry_resources if er.resource]

        data.append(
            PublishedEntryListItem(
                slug=entry.slug,
                title=entry.title,
                entry_type=entry.entry_type.slug if entry.entry_type else settings.PUBLISHING_UNKNOWN_ENTRY_TYPE,
                summary=entry.summary,
                published_at=entry.published_at,
                collections=collection_slugs,
                assets=asset_slugs,
                resources=resource_slugs,
            )
        )

    return PublishedEntriesResponse(
        data=data,
        meta=PaginationMeta(
            total=total,
            page=(offset // limit) + 1,
            limit=limit,
            offset=offset,
        ),
    )


@router.get(
    "/{workspace_slug}/entries/{slug}",
    response_model=PublishedEntryRead,
    summary="Get Published Entry",
)
async def get_published_entry(
    slug: str,
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> PublishedEntryRead:
    """
    Get a single published entry by slug.

    Returns full entry content including Markdown body.

    **Filters:**
    - Only returns entry if `status = 'published'`

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:published_entries OR read:all_entries

    **Raises:**
    - 404: Entry not found or not published
    """
    api_client, group, perms = context

    # Require permission to read entries
    perms.require_any_permission([Permissions.READ_PUBLISHED_ENTRIES, Permissions.READ_ALL_ENTRIES], "published entry")

    # Query published entry
    entry = (
        session.query(Entries)
        .filter(
            Entries.group_id == group.id,
            Entries.slug == slug,
            Entries.status == settings.PUBLISHING_DEFAULT_STATUS,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Get collections with full details
    collections = [
        PublishedCollectionSummary(
            slug=ec.collection.slug,
            name=ec.collection.name,
            description=ec.collection.description,
            is_smart=ec.collection.is_smart,
            smart_rules=ec.collection.smart_rules,
            metadata=ec.collection.metadata_json,
            entry_count=0,  # Not needed in entry context
            sort_order=ec.collection.sort_order,
            icon=ec.collection.icon,
            color=ec.collection.color,
        )
        for ec in entry.entry_collections
        if ec.collection
    ]

    # Get resources for this entry
    resources = [
        PublishedResourceRead(
            slug=er.resource.slug,
            name=er.resource.name,
            resource_type=er.resource.resource_type,
            description=er.resource.description,
            url=er.resource.url,
            external_id=er.resource.external_id,
            role=er.role,
            quantity=er.quantity,
            unit=er.unit,
            position=er.position,
        )
        for er in entry.entry_resources
        if er.resource  # Defensive check
    ]

    # Get assets for this entry
    assets = [
        PublishedAssetRead(
            slug=ea.asset.slug,
            name=ea.asset.name,
            mime_type=ea.asset.mime_type,
            asset_type=ea.asset.asset_type,
            file_size=ea.asset.file_size,
            width=ea.asset.width,
            height=ea.asset.height,
            alt_text=ea.asset.alt_text or ea.caption,  # Use caption if no alt_text
            description=ea.asset.description,
            public_url=ea.asset.public_url or f"/api/publish/{group.slug}/assets/{ea.asset.slug}/file",
        )
        for ea in entry.entry_assets
        if ea.asset  # Defensive check
    ]

    return PublishedEntryRead(
        slug=entry.slug,
        title=entry.title,
        entry_type=entry.entry_type.slug if entry.entry_type else settings.PUBLISHING_UNKNOWN_ENTRY_TYPE,
        summary=entry.summary,
        content_markdown=entry.content_markdown,
        published_at=entry.published_at,
        metadata=entry.metadata_json,
        collections=collections,
        resources=resources,
        assets=assets,
    )


@router.get(
    "/{workspace_slug}/collections",
    response_model=PublishedCollectionsResponse,
    summary="List Collections",
)
async def list_published_collections(
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
    limit: int = Query(settings.PUBLISHING_DEFAULT_PAGE_SIZE, ge=1, le=settings.PUBLISHING_MAX_PAGE_SIZE, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> PublishedCollectionsResponse:
    """
    List all collections in the workspace.

    Returns collection summaries with entry counts (published entries only).

    **Use case**: Building navigation menus, collection indexes.

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:collections
    """
    api_client, group, perms = context

    # Require permission to read collections
    perms.require_permission(Permissions.READ_COLLECTIONS, "collections")

    # Get total count
    total = session.query(Collections).filter(Collections.group_id == group.id).count()

    # Get paginated collections for this workspace
    collections = (
        session.query(Collections)
        .filter(Collections.group_id == group.id)
        .order_by(Collections.sort_order, Collections.name)
        .limit(limit)
        .offset(offset)
        .all()
    )

    # Build response with entry counts
    from marvin.db.models.platform import EntryCollections

    result = []
    for collection in collections:
        # Count published entries in this collection
        entry_count = (
            session.query(Entries)
            .join(EntryCollections)
            .filter(
                EntryCollections.collection_id == collection.id,
                Entries.status == settings.PUBLISHING_DEFAULT_STATUS,
            )
            .count()
        )

        result.append(
            PublishedCollectionSummary(
                slug=collection.slug,
                name=collection.name,
                description=collection.description,
                is_smart=collection.is_smart,
                smart_rules=collection.smart_rules,
                metadata=collection.metadata_json,
                entry_count=entry_count,
                sort_order=collection.sort_order,
                icon=collection.icon,
                color=collection.color,
            )
        )

    return PublishedCollectionsResponse(
        data=result,
        meta=PaginationMeta(
            total=total,
            page=(offset // limit) + 1,
            limit=limit,
            offset=offset,
        ),
    )


@router.get(
    "/{workspace_slug}/collections/{collection_slug}",
    response_model=PublishedCollectionRead,
    summary="Get Collection with Entries",
)
async def get_published_collection(
    collection_slug: str,
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> PublishedCollectionRead:
    """
    Get a collection with its published entries.

    Returns collection metadata and all published entries in the collection.

    **Filters:**
    - Only includes entries with `status = 'published'`

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:collections

    **Raises:**
    - 404: Collection not found
    """
    api_client, group, perms = context

    # Require permission to read collections
    perms.require_permission(Permissions.READ_COLLECTIONS, "collection")

    # Get collection
    collection = (
        session.query(Collections)
        .filter(
            Collections.group_id == group.id,
            Collections.slug == collection_slug,
        )
        .first()
    )

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Get published entries in this collection
    from marvin.db.models.platform import EntryCollections

    entries = (
        session.query(Entries)
        .join(EntryCollections)
        .filter(
            EntryCollections.collection_id == collection.id,
            Entries.status == settings.PUBLISHING_DEFAULT_STATUS,
        )
        .order_by(EntryCollections.sort_order.asc(), Entries.published_at.desc())
        .all()
    )

    # Convert to list items
    entry_items = []
    for entry in entries:
        # Get collection slugs for each entry
        collection_slugs = [ec.collection.slug for ec in entry.entry_collections if ec.collection]

        # Get asset slugs
        asset_slugs = [ea.asset.slug for ea in entry.entry_assets if ea.asset]

        # Get resource slugs
        resource_slugs = [er.resource.slug for er in entry.entry_resources if er.resource]

        entry_items.append(
            PublishedEntryListItem(
                slug=entry.slug,
                title=entry.title,
                entry_type=entry.entry_type.slug if entry.entry_type else settings.PUBLISHING_UNKNOWN_ENTRY_TYPE,
                summary=entry.summary,
                published_at=entry.published_at,
                collections=collection_slugs,
                assets=asset_slugs,
                resources=resource_slugs,
            )
        )

    return PublishedCollectionRead(
        slug=collection.slug,
        name=collection.name,
        description=collection.description,
        is_smart=collection.is_smart,
        smart_rules=collection.smart_rules,
        metadata=collection.metadata_json,
        entry_count=len(entry_items),
        entries=entry_items,
    )


@router.get(
    "/{workspace_slug}/assets",
    response_model=PublishedAssetsResponse,
    summary="List Assets",
)
async def list_published_assets(
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
    type: str | None = Query(None, description="Filter by MIME type prefix (image, video, audio, application)"),
    limit: int = Query(settings.PUBLISHING_DEFAULT_PAGE_SIZE, ge=1, le=settings.PUBLISHING_MAX_PAGE_SIZE, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> PublishedAssetsResponse:
    """
    List all assets in the workspace.

    Returns asset metadata for external sites to reference.

    **Filters:**
    - `type`: Filter by MIME type prefix (image, video, audio, application)
    - Scoped to the workspace associated with the API client

    **Use cases:**
    - `?type=image` - Get all images
    - `?type=video` - Get all videos
    - Build asset galleries, media libraries

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:assets
    """
    api_client, group, perms = context

    # Require permission to read assets
    perms.require_permission(Permissions.READ_ASSETS, "assets")

    # Build query for assets
    query = session.query(Assets).filter(
        Assets.group_id == group.id,
    )

    # Filter by MIME type prefix if specified
    if type:
        query = query.filter(Assets.mime_type.like(f"{type}/%"))

    # Get total count
    total = query.count()

    # Apply pagination
    assets = query.order_by(Assets.name).offset(offset).limit(limit).all()

    # Convert to response schema
    data = []
    for asset in assets:
        # Get published entry slugs that use this asset
        entry_slugs = [ea.entry.slug for ea in asset.entry_assets if ea.entry and ea.entry.status == settings.PUBLISHING_DEFAULT_STATUS]

        data.append(
            PublishedAssetRead(
                slug=asset.slug,
                name=asset.name,
                mime_type=asset.mime_type,
                asset_type=asset.asset_type,
                file_size=asset.file_size,
                width=asset.width,
                height=asset.height,
                alt_text=asset.alt_text,
                description=asset.description,
                public_url=asset.public_url or f"/api/publish/{group.slug}/assets/{asset.slug}/file",
                metadata=asset.metadata_,
                entries=entry_slugs,
            )
        )

    return PublishedAssetsResponse(
        data=data,
        meta=PaginationMeta(
            total=total,
            page=(offset // limit) + 1,
            limit=limit,
            offset=offset,
        ),
    )


@router.get(
    "/{workspace_slug}/assets/{asset_slug}",
    response_model=PublishedAssetRead,
    summary="Get Published Asset Metadata",
)
async def get_published_asset(
    asset_slug: str,
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> PublishedAssetRead:
    """
    Get asset metadata for published content.

    Returns asset information (name, mime_type, dimensions, alt_text) for consumption
    by external sites.

    **Use case**: Astro site fetches asset metadata to build <img> tags with proper
    dimensions and alt text.

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:assets

    **Raises:**
    - 404: Asset not found

    **Note**: Actual file serving (GET /assets/{slug}/file) is deferred to Phase 7.
    """
    api_client, group, perms = context

    # Require permission to read assets
    perms.require_permission(Permissions.READ_ASSETS, "asset")

    asset = (
        session.query(Assets)
        .filter(
            Assets.group_id == group.id,
            Assets.slug == asset_slug,
        )
        .first()
    )

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get published entry slugs that use this asset
    entry_slugs = [ea.entry.slug for ea in asset.entry_assets if ea.entry and ea.entry.status == settings.PUBLISHING_DEFAULT_STATUS]

    return PublishedAssetRead(
        slug=asset.slug,
        name=asset.name,
        mime_type=asset.mime_type,
        asset_type=asset.asset_type,
        file_size=asset.file_size,
        width=asset.width,
        height=asset.height,
        alt_text=asset.alt_text,
        description=asset.description,
        public_url=asset.public_url or f"/api/publish/{group.slug}/assets/{asset.slug}/file",
        metadata=asset.metadata_,
        entries=entry_slugs,
    )


@router.get(
    "/{workspace_slug}/assets/{asset_slug}/file",
    summary="Serve Asset File",
)
async def serve_asset_file(
    asset_slug: str,
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
):
    """
    Serve the actual asset file content.

    This endpoint proxies through to the storage provider to serve the asset file.
    For local storage, it redirects to the static file path.
    For S3 storage, it could generate a signed URL or proxy the content.

    **Use case**: Browsers fetching images, PDFs, videos via their public URL.

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:assets

    **Raises:**
    - 404: Asset not found
    """
    from fastapi.responses import RedirectResponse

    api_client, group, perms = context

    # Require permission to access asset files
    perms.require_permission(Permissions.READ_ASSETS, "asset file")

    asset = (
        session.query(Assets)
        .filter(
            Assets.group_id == group.id,
            Assets.slug == asset_slug,
        )
        .first()
    )

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # For local storage, redirect to the static file URL
    if asset.storage_provider == "local":
        return RedirectResponse(url=f"/assets/{asset.storage_key}")

    # For S3 or other providers, use the public_url if available
    if asset.public_url:
        return RedirectResponse(url=asset.public_url)

    # Fallback error
    raise HTTPException(status_code=500, detail="Asset file URL not available")


@router.get(
    "/{workspace_slug}/resources",
    response_model=PublishedResourcesResponse,
    summary="List Resources",
)
async def list_published_resources(
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    limit: int = Query(settings.PUBLISHING_DEFAULT_PAGE_SIZE, ge=1, le=settings.PUBLISHING_MAX_PAGE_SIZE, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> PublishedResourcesResponse:
    """
    List all resources in the workspace.

    Returns resource metadata for external sites to reference.

    **Filters:**
    - `resource_type`: Filter by resource type (fabric, tool, supplier, etc.)
    - Scoped to the workspace associated with the API client

    **Use cases:**
    - `?resource_type=fabric` - Get all fabrics
    - `?resource_type=tool` - Get all tools
    - Build resource directories, material libraries

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:resources
    """
    api_client, group, perms = context

    # Require permission to read resources
    perms.require_permission(Permissions.READ_RESOURCES, "resources")

    # Build query for resources
    query = session.query(Resources).filter(
        Resources.group_id == group.id,
    )

    # Filter by resource type if specified
    if resource_type:
        query = query.filter(Resources.resource_type == resource_type)

    # Get total count
    total = query.count()

    # Apply pagination
    resources = query.order_by(Resources.name).offset(offset).limit(limit).all()

    # Convert to response schema
    data = []
    for resource in resources:
        # Get published entry slugs that reference this resource
        entry_slugs = [er.entry.slug for er in resource.entry_resources if er.entry and er.entry.status == settings.PUBLISHING_DEFAULT_STATUS]

        data.append(
            PublishedResourceSummary(
                slug=resource.slug,
                name=resource.name,
                resource_type=resource.resource_type,
                description=resource.description,
                url=resource.url,
                external_id=resource.external_id,
                metadata=resource.metadata_,
                entries=entry_slugs,
            )
        )

    return PublishedResourcesResponse(
        data=data,
        meta=PaginationMeta(
            total=total,
            page=(offset // limit) + 1,
            limit=limit,
            offset=offset,
        ),
    )


@router.get(
    "/{workspace_slug}/resources/{resource_slug}",
    response_model=PublishedResourceSummary,
    summary="Get Resource",
)
async def get_published_resource(
    resource_slug: str,
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> PublishedResourceSummary:
    """
    Get a single resource by slug.

    Returns resource metadata for external sites to reference.

    **Use case**: Resource detail pages, material information displays.

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:resources

    **Raises:**
    - 404: Resource not found
    """
    api_client, group, perms = context

    # Require permission to read resources
    perms.require_permission(Permissions.READ_RESOURCES, "resource")

    # Query resource
    resource = (
        session.query(Resources)
        .filter(
            Resources.group_id == group.id,
            Resources.slug == resource_slug,
        )
        .first()
    )

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get published entry slugs that reference this resource
    entry_slugs = [er.entry.slug for er in resource.entry_resources if er.entry and er.entry.status == settings.PUBLISHING_DEFAULT_STATUS]

    return PublishedResourceSummary(
        slug=resource.slug,
        name=resource.name,
        resource_type=resource.resource_type,
        description=resource.description,
        url=resource.url,
        external_id=resource.external_id,
        metadata=resource.metadata_,
        entries=entry_slugs,
    )


@router.get(
    "/{workspace_slug}/resources/{resource_slug}/entries",
    response_model=list[PublishedEntryListItem],
    summary="Get Resource Entries",
)
async def get_resource_entries(
    resource_slug: str,
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> list[PublishedEntryListItem]:
    """
    Get all published entries that reference a resource.

    Returns entries that use this resource (e.g., projects using a fabric).

    **Filters:**
    - Only returns entries with `status = 'published'`

    **Use case**: "View projects using this fabric" links on resource pages.

    **Authentication**: Requires API client token (marvin_sk_*)
    **Permissions**: read:resources

    **Raises:**
    - 404: Resource not found
    """
    api_client, group, perms = context

    # Require permission to read resources
    perms.require_permission(Permissions.READ_RESOURCES, "resource entries")

    # Get resource
    resource = (
        session.query(Resources)
        .filter(
            Resources.group_id == group.id,
            Resources.slug == resource_slug,
        )
        .first()
    )

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get published entries that reference this resource
    from marvin.db.models.platform import EntryResources

    entries = (
        session.query(Entries)
        .join(EntryResources)
        .filter(
            EntryResources.resource_id == resource.id,
            Entries.status == settings.PUBLISHING_DEFAULT_STATUS,
        )
        .order_by(Entries.published_at.desc())
        .all()
    )

    # Convert to list items
    entry_items = []
    for entry in entries:
        # Get collection slugs for each entry
        collection_slugs = [ec.collection.slug for ec in entry.entry_collections if ec.collection]

        # Get asset slugs
        asset_slugs = [ea.asset.slug for ea in entry.entry_assets if ea.asset]

        # Get resource slugs
        resource_slugs = [er.resource.slug for er in entry.entry_resources if er.resource]

        entry_items.append(
            PublishedEntryListItem(
                slug=entry.slug,
                title=entry.title,
                entry_type=entry.entry_type.slug if entry.entry_type else settings.PUBLISHING_UNKNOWN_ENTRY_TYPE,
                summary=entry.summary,
                published_at=entry.published_at,
                collections=collection_slugs,
                assets=asset_slugs,
                resources=resource_slugs,
            )
        )

    return entry_items
