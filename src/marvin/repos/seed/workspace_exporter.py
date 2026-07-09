"""Workspace exporter for dumping workspace data to JSON format."""

import logging
from typing import Any

from marvin.repos.repository_factory import AllRepositories


class WorkspaceExporter:
    """Exports complete workspace data to JSON format.

    Produces the same format that WorkspaceSeedLoader imports:
    - collections
    - entry_types (workspace-scoped only)
    - entries (with collection assignments)
    """

    def __init__(self, repos: AllRepositories, logger: logging.Logger | None = None):
        """Initialize exporter with repository access.

        Args:
            repos: Repository factory for database operations
            logger: Optional logger instance
        """
        self.repos = repos
        self.logger = logger or logging.getLogger(__name__)

    def export_workspace(self, include_system_types: bool = False) -> dict[str, Any]:
        """Export complete workspace data to JSON-serializable dict.

        Args:
            include_system_types: Whether to include system entry types in export

        Returns:
            Dictionary with workspace data in seed format
        """
        self.logger.info("Exporting workspace data...")

        export_data = {
            "version": 1,
            "workspace": self._export_workspace_metadata(),
            "site": self._export_site_preferences(),
            "collections": self._export_collections(),
            "entry_types": self._export_entry_types(include_system_types),
            "entries": self._export_entries(),
        }

        self.logger.info(
            f"Export complete: {len(export_data['collections'])} collections, "
            f"{len(export_data['entry_types'])} entry types, "
            f"{len(export_data['entries'])} entries"
        )

        return export_data

    def _export_workspace_metadata(self) -> dict[str, Any]:
        """Export workspace metadata.

        Returns:
            Dictionary with workspace name and slug
        """
        workspace = self.repos.groups.get_one(self.repos.group_id)

        if not workspace:
            return {}

        return {
            "name": workspace.name,
            "slug": workspace.slug,
            # Note: ownerEmail is not exported - it's only used during initial import
        }

    def _export_site_preferences(self) -> dict[str, Any]:
        """Export site preferences/configuration.

        Returns:
            Dictionary with site configuration fields
        """
        prefs_list = self.repos.group_preferences.multi_query({"group_id": self.repos.group_id})

        if not prefs_list:
            return {}

        prefs = prefs_list[0]

        return {
            "title": prefs.site_title,
            "tagline": prefs.site_tagline,
            "description": prefs.site_description,
            "canonicalUrl": prefs.site_canonical_url,
            "logo": prefs.site_logo,
            "favicon": prefs.site_favicon,
            "locale": prefs.site_locale,
            "timezone": prefs.site_timezone,
            "contactEmail": prefs.site_contact_email,
            "social": prefs.site_social_json,
            "metadataJson": prefs.site_metadata_json,
        }

    def _export_collections(self) -> list[dict[str, Any]]:
        """Export all collections.

        Returns:
            List of collection dicts in seed format
        """
        collections = self.repos.collections.get_all(
            limit=None,  # Get all
            order_by="sort_order",
        )

        exported = []
        for coll in collections:
            exported.append(
                {
                    "name": coll.name,
                    "slug": coll.slug,
                    "description": coll.description,
                    "sortOrder": coll.sort_order,
                    "icon": coll.icon,
                    "color": coll.color,
                    "metadataJson": coll.metadata_json,
                }
            )

        return exported

    def _export_entry_types(self, include_system: bool) -> list[dict[str, Any]]:
        """Export entry types.

        Args:
            include_system: Whether to include system entry types

        Returns:
            List of entry type dicts in seed format
        """
        # Get all entry types (includes workspace and system types via repository filters)
        entry_types = self.repos.entry_types.get_all(
            limit=None,  # Get all
            order_by="sort_order",
        )

        exported = []
        for et in entry_types:
            # Skip system types unless requested
            if not include_system and et.group_id is None:
                continue

            exported.append(
                {
                    "name": et.name,
                    "slug": et.slug,
                    "icon": et.icon,
                    "color": et.color,
                    "description": et.description,
                    "sortOrder": et.sort_order,
                    "schemaJson": et.content_schema,
                }
            )

        return exported

    def _export_entries(self) -> list[dict[str, Any]]:
        """Export all entries with their collection assignments.

        Returns:
            List of entry dicts in seed format
        """
        entries = self.repos.entries.get_all(
            limit=None,  # Get all
            order_by="slug",
        )

        exported = []
        for entry in entries:
            # Get entry type
            entry_type = self.repos.entry_types.get_one(entry.entry_type_id)
            if not entry_type:
                self.logger.warning(f"Entry type not found for entry: {entry.slug}")
                continue

            # Get collection assignments
            collections_data = self._get_entry_collections(entry.id)

            entry_dict = {
                "entryType": entry_type.slug,
                "title": entry.title,
                "slug": entry.slug,
                "status": entry.status,
                "summary": entry.summary,
                "description": entry.description,
                "data": entry.data_json,
                "metadataJson": entry.metadata_json,
                "publishAt": entry.publish_at.isoformat() if entry.publish_at else None,
                "expireAt": entry.expire_at.isoformat() if entry.expire_at else None,
            }

            # Add entryTypeScope if using a system type (for explicit re-import)
            if entry_type.group_id is None:
                entry_dict["entryTypeScope"] = "system"

            # Only add collections array if there are any
            if collections_data:
                entry_dict["collections"] = collections_data

            exported.append(entry_dict)

        return exported

    def _get_entry_collections(self, entry_id: str) -> list[dict[str, Any]]:
        """Get collection assignments for an entry.

        Args:
            entry_id: UUID of the entry

        Returns:
            List of {slug: str, order: int} dicts
        """
        from marvin.db.models.platform import EntryCollections

        # Query junction table
        assignments = self.repos.session.query(EntryCollections).filter(EntryCollections.entry_id == entry_id).all()

        collections_data = []
        for assignment in assignments:
            # Get collection to get its slug
            collection = self.repos.collections.get_one(assignment.collection_id)
            if collection:
                collections_data.append(
                    {
                        "slug": collection.slug,
                        "order": assignment.sort_order,
                    }
                )

        return collections_data
