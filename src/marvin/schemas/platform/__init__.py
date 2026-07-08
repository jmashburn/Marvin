"""Platform schemas."""

from .api_clients import (
    APIClientCreate,
    APIClientRead,
    APIClientSummary,
    APIClientUpdate,
    APIClientWithToken,
)
from .assets import (
    AssetCreate,
    AssetCreateInternal,
    AssetPlacement,
    AssetRead,
    AssetSummary,
    AssetUpdate,
    AssetUploadRequest,
    EntryAssetRead,
)
from .collections import (
    CollectionCreate,
    CollectionRead,
    CollectionSummary,
    CollectionUpdate,
)
from .entries import (
    EntryCreate,
    EntryRead,
    EntrySummary,
    EntryUpdate,
)
from .entry_types import (
    EntryTypeCreate,
    EntryTypeRead,
    EntryTypeSummary,
    EntryTypeUpdate,
)
from .resources import (
    ResourceCreate,
    ResourceRead,
    ResourceSummary,
    ResourceUpdate,
)

__all__ = [
    "APIClientCreate",
    "APIClientRead",
    "APIClientSummary",
    "APIClientUpdate",
    "APIClientWithToken",
    "AssetCreate",
    "AssetCreateInternal",
    "AssetPlacement",
    "AssetRead",
    "AssetSummary",
    "AssetUpdate",
    "AssetUploadRequest",
    "CollectionCreate",
    "CollectionRead",
    "CollectionSummary",
    "CollectionUpdate",
    "EntryAssetRead",
    "EntryCreate",
    "EntryRead",
    "EntrySummary",
    "EntryTypeCreate",
    "EntryTypeRead",
    "EntryTypeSummary",
    "EntryTypeUpdate",
    "EntryUpdate",
    "ResourceCreate",
    "ResourceRead",
    "ResourceSummary",
    "ResourceUpdate",
    # Legacy aliases for backward compatibility
    "SiteClientCreate",
    "SiteClientRead",
    "SiteClientUpdate",
]

# Legacy aliases for backward compatibility with frontend
SiteClientCreate = APIClientCreate
SiteClientRead = APIClientRead
SiteClientUpdate = APIClientUpdate

# Rebuild models to resolve forward references after all schemas are imported
EntryRead.model_rebuild()
EntrySummary.model_rebuild()
