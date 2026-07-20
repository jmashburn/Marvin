"""Platform models."""

from .api_clients import APIClients
from .asset_tags import AssetTags
from .assets import Assets
from .collections import Collections
from .entries import Entries
from .entry_assets import EntryAssets
from .entry_collections import EntryCollections
from .entry_resources import EntryResources
from .entry_types import EntryTypes
from .event_log import EventLogModel
from .entry_tags import EntryTags
from .resource_tags import ResourceTags
from .resources import Resources
from .scheduled_tasks import ScheduledTaskExecutionLogModel, ScheduledTaskModel
from .tags import Tags

# isort: split
# CODE_GEN_ID: PLATFORM_MODEL_IMPORTS
# END: PLATFORM_MODEL_IMPORTS

__all__ = [
    "APIClients",
    "AssetTags",
    "Assets",
    "Collections",
    "Entries",
    "EntryAssets",
    "EntryCollections",
    "EntryResources",
    "EntryTags",
    "EntryTypes",
    "EventLogModel",
    "ResourceTags",
    "Resources",
    "ScheduledTaskExecutionLogModel",
    "ScheduledTaskModel",
    "Tags",
    # CODE_GEN_ID: PLATFORM_MODEL_ALL
    # END: PLATFORM_MODEL_ALL
]
