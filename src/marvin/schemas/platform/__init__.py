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
    AssetPlacement,
    AssetRead,
    AssetSummary,
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
    "AssetPlacement",
    "AssetRead",
    "AssetSummary",
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
]
