"""
Publishing API controller.

Provides read-only access to published content for external sites (Astro, etc.).
All routes require API client token authentication (marvin_sk_ prefix).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from marvin.core.config import get_app_settings
from marvin.core.dependencies import get_publishing_context
from marvin.db.db_setup import generate_session
from marvin.db.models.platform import APIClients, Assets, Collections, Entries
from marvin.repos.all_repositories import get_repositories
from marvin.schemas.group import GroupRead
from marvin.schemas.publishing import (
    PublishedAssetRead,
    PublishedCollectionRead,
    PublishedCollectionSummary,
    PublishedEntriesResponse,
    PublishedEntryListItem,
    PublishedEntryRead,
    PublishedResourceRead,
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
    """
    api_client, group = context

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
    """
    api_client, group = context

    # Get group preferences (includes site configuration)
    from marvin.db.models.groups import GroupPreferencesModel

    prefs = (
        session.query(GroupPreferencesModel)
        .filter(GroupPreferencesModel.group_id == group.id)
        .first()
    )

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
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(
        settings.PUBLISHING_DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.PUBLISHING_MAX_PAGE_SIZE,
        description="Items per page"
    ),
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
    """
    api_client, group = context

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

        entry_type_obj = (
            session.query(EntryTypes)
            .filter(EntryTypes.group_id == group.id, EntryTypes.slug == entry_type)
            .first()
        )

        if not entry_type_obj:
            # Return empty list if entry type doesn't exist
            return PublishedEntriesResponse(
                data=[],
                meta={"total": 0, "page": page, "limit": limit},
            )

        query = query.filter(Entries.entry_type_id == entry_type_obj.id)

    # Filter by collection if specified
    if collection:
        from marvin.db.models.platform import EntryCollections

        # Get collection
        collection_obj = (
            session.query(Collections)
            .filter(Collections.group_id == group.id, Collections.slug == collection)
            .first()
        )

        if not collection_obj:
            # Return empty list if collection doesn't exist
            return PublishedEntriesResponse(
                data=[],
                meta={"total": 0, "page": page, "limit": limit},
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
    offset = (page - 1) * limit
    entries = query.order_by(Entries.published_at.desc()).offset(offset).limit(limit).all()

    # Convert to list items
    data = []
    for entry in entries:
        # Get collection slugs
        collection_slugs = [ec.collection.slug for ec in entry.entry_collections if ec.collection]

        data.append(
            PublishedEntryListItem(
                slug=entry.slug,
                title=entry.title,
                entry_type=entry.entry_type.slug if entry.entry_type else settings.PUBLISHING_UNKNOWN_ENTRY_TYPE,
                summary=entry.summary,
                published_at=entry.published_at,
                collections=collection_slugs,
            )
        )

    return PublishedEntriesResponse(
        data=data,
        meta={
            "total": total,
            "page": page,
            "limit": limit,
        },
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

    **Raises:**
    - 404: Entry not found or not published
    """
    api_client, group = context

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

    # Get collection slugs
    collection_slugs = [ec.collection.slug for ec in entry.entry_collections if ec.collection]

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
            width=ea.asset.width,
            height=ea.asset.height,
            alt_text=ea.asset.alt_text or ea.caption,  # Use caption if no alt_text
            file_url=f"/api/publish/{group.slug}/assets/{ea.asset.slug}/file",
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
        collections=collection_slugs,
        resources=resources,
        assets=assets,
    )


@router.get(
    "/{workspace_slug}/collections",
    response_model=list[PublishedCollectionSummary],
    summary="List Collections",
)
async def list_published_collections(
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> list[PublishedCollectionSummary]:
    """
    List all collections in the workspace.

    Returns collection summaries with entry counts (published entries only).

    **Use case**: Building navigation menus, collection indexes.

    **Authentication**: Requires API client token (marvin_sk_*)
    """
    api_client, group = context

    # Get all collections for this workspace
    collections = (
        session.query(Collections)
        .filter(Collections.group_id == group.id)
        .order_by(Collections.sort_order, Collections.name)
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
                entry_count=entry_count,
                sort_order=collection.sort_order,
                icon=collection.icon,
                color=collection.color,
            )
        )

    return result


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

    **Raises:**
    - 404: Collection not found
    """
    api_client, group = context

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
        .order_by(Entries.published_at.desc())
        .all()
    )

    # Convert to list items
    entry_items = []
    for entry in entries:
        # Get collection slugs for each entry
        collection_slugs = [ec.collection.slug for ec in entry.entry_collections if ec.collection]

        entry_items.append(
            PublishedEntryListItem(
                slug=entry.slug,
                title=entry.title,
                entry_type=entry.entry_type.slug if entry.entry_type else settings.PUBLISHING_UNKNOWN_ENTRY_TYPE,
                summary=entry.summary,
                published_at=entry.published_at,
                collections=collection_slugs,
            )
        )

    return PublishedCollectionRead(
        slug=collection.slug,
        name=collection.name,
        description=collection.description,
        entry_count=len(entry_items),
        entries=entry_items,
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

    **Raises:**
    - 404: Asset not found

    **Note**: Actual file serving (GET /assets/{slug}/file) is deferred to Phase 7.
    """
    api_client, group = context

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

    return PublishedAssetRead(
        slug=asset.slug,
        name=asset.name,
        mime_type=asset.mime_type,
        width=asset.width,
        height=asset.height,
        alt_text=asset.alt_text,
        file_url=f"/api/publish/{group.slug}/assets/{asset.slug}/file",
    )
