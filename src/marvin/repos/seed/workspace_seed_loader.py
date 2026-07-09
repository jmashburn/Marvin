"""Complete workspace seed loader for importing workspace data from JSON."""

import json
import logging
from pathlib import Path
from typing import Any

from marvin.repos.repository_factory import AllRepositories


class WorkspaceSeedLoader:
    """Loads complete workspace data from seed files.

    Supports the full workspace seed format including:
    - workspace metadata
    - site configuration
    - collections
    - entry_types
    - entries (with collection assignments)
    - resources
    - assets
    """

    def __init__(self, repos: AllRepositories, logger: logging.Logger | None = None):
        """Initialize loader with repository access.

        Args:
            repos: Repository factory for database operations
            logger: Optional logger instance
        """
        self.repos = repos
        self.logger = logger or logging.getLogger(__name__)

    def load_seed_file(self, seed_file: Path) -> dict[str, int]:
        """Load a complete workspace seed from a JSON file.

        Args:
            seed_file: Path to workspace seed JSON file

        Returns:
            Dictionary with counts by type
        """
        self.logger.info(f"Loading workspace seed from: {seed_file}")

        with open(seed_file, "r") as f:
            data = json.load(f)

        results = {
            "collections": 0,
            "entry_types": 0,
            "entries": 0,
            "resources": 0,
            "assets": 0,
            "errors": 0,
        }

        # 0. Create or find workspace from seed file
        workspace_data = data.get("workspace")
        if workspace_data:
            workspace = self._ensure_workspace(workspace_data)
            # Switch repos to this workspace's context
            from marvin.repos.all_repositories import get_repositories

            self.repos = get_repositories(self.repos.session, group_id=workspace.id)
            self.logger.info(f"Using workspace: {workspace.name} ({workspace.slug})")

            # Update site preferences if provided
            site_data = data.get("site")
            if site_data:
                self._update_site_preferences(site_data)

        # Process in order: collections -> entry_types -> entries
        # (entries reference collections and entry types)

        # 1. Collections
        collections_data = data.get("collections", [])
        if collections_data:
            self.logger.info(f"Creating {len(collections_data)} collections...")
            for coll_data in collections_data:
                try:
                    self._create_collection(coll_data)
                    results["collections"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to create collection {coll_data.get('slug')}: {e}")
                    results["errors"] += 1

        # 2. Entry Types
        entry_types_data = data.get("entry_types", [])
        if entry_types_data:
            self.logger.info(f"Creating {len(entry_types_data)} entry types...")
            for et_data in entry_types_data:
                try:
                    self._create_entry_type(et_data)
                    results["entry_types"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to create entry type {et_data.get('slug')}: {e}")
                    results["errors"] += 1

        # 3. Entries
        entries_data = data.get("entries", [])
        if entries_data:
            self.logger.info(f"Creating {len(entries_data)} entries...")
            for entry_data in entries_data:
                try:
                    self._create_entry(entry_data)
                    results["entries"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to create entry {entry_data.get('slug')}: {e}")
                    results["errors"] += 1

        self.logger.info(
            f"Seed loaded: {results['collections']} collections, "
            f"{results['entry_types']} entry types, "
            f"{results['entries']} entries, "
            f"{results['errors']} errors"
        )

        return results

    def _ensure_workspace(self, data: dict[str, Any]):
        """Create workspace if it doesn't exist, or return existing one.

        Args:
            data: Workspace data from seed file

        Returns:
            GroupRead: The workspace/group
        """
        from marvin.schemas.group.group import GroupCreate
        from marvin.services.group.group_service import GroupService

        # Check if workspace exists by slug
        existing_groups = self.repos.groups.multi_query({"slug": data["slug"]})
        if existing_groups:
            self.logger.info(f"Workspace already exists: {data['slug']}")
            return existing_groups[0]

        # Create new workspace
        group_create = GroupCreate(
            name=data["name"],
            slug=data.get("slug"),  # Optional, will be auto-generated if not provided
        )

        workspace = GroupService.create_group(self.repos, group_create)
        self.logger.info(f"Created workspace: {workspace.name} ({workspace.slug})")
        return workspace

    def _update_site_preferences(self, data: dict[str, Any]) -> None:
        """Update site preferences for the workspace.

        Args:
            data: Site configuration data from seed file
        """
        # Map camelCase JSON fields to snake_case database fields
        update_data = {
            "site_title": data.get("title"),
            "site_tagline": data.get("tagline"),
            "site_description": data.get("description"),
            "site_canonical_url": data.get("canonicalUrl"),
            "site_logo": data.get("logo"),
            "site_favicon": data.get("favicon"),
            "site_locale": data.get("locale"),
            "site_timezone": data.get("timezone"),
            "site_contact_email": data.get("contactEmail"),
            "site_social_json": data.get("social"),
            "site_metadata_json": data.get("metadataJson"),
        }

        # Remove None values to avoid overwriting existing data with nulls
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if update_data:
            # Update preferences using the preferences repository
            # Use multi_query to find by group_id since get_one uses primary key
            prefs_list = self.repos.group_preferences.multi_query({"group_id": self.repos.group_id})
            if prefs_list:
                prefs = prefs_list[0]
                self.repos.group_preferences.update(prefs.id, update_data)
                self.logger.info(f"Updated site preferences ({len(update_data)} fields)")
            else:
                self.logger.warning("Group preferences not found - cannot update site settings")

    def _create_collection(self, data: dict[str, Any]) -> None:
        """Create a collection if it doesn't exist.

        Args:
            data: Collection data from seed file
        """
        # Check if exists
        existing = self.repos.collections.multi_query({"slug": data["slug"]})
        if existing:
            self.logger.debug(f"Collection already exists: {data['slug']}")
            return

        # Create collection
        create_data = {
            "name": data["name"],
            "slug": data["slug"],
            "description": data.get("description"),
            "sort_order": data.get("sortOrder", 0),
            "icon": data.get("icon"),
            "color": data.get("color"),
            "metadata_json": data.get("metadataJson"),
        }

        self.repos.collections.create(create_data)
        self.logger.info(f"Created collection: {data['slug']}")

    def _create_entry_type(self, data: dict[str, Any]) -> None:
        """Create an entry type if it doesn't exist.

        Args:
            data: Entry type data from seed file
        """
        # Check if exists in THIS workspace (not system types)
        # Need to check both slug AND group_id to respect UNIQUE (group_id, slug) constraint
        existing = self.repos.entry_types.multi_query({"slug": data["slug"], "group_id": self.repos.group_id})
        if existing:
            self.logger.debug(f"Entry type already exists in workspace: {data['slug']}")
            return

        # Create entry type
        create_data = {
            "name": data["name"],
            "slug": data["slug"],
            "icon": data.get("icon"),
            "color": data.get("color"),
            "description": data.get("description"),
            "sort_order": data.get("sortOrder", 0),
            "content_schema": data.get("schemaJson", {}),
        }

        self.repos.entry_types.create(create_data)
        self.logger.info(f"Created entry type: {data['slug']}")

    def _create_entry(self, data: dict[str, Any]) -> None:
        """Create an entry with collection assignments.

        Args:
            data: Entry data from seed file
        """
        # Check if exists
        existing = self.repos.entries.multi_query({"slug": data["slug"]})
        if existing:
            self.logger.debug(f"Entry already exists: {data['slug']}")
            return

        # Get entry type - handle explicit scope or auto-prefer workspace over system
        entry_type_slug = data["entryType"]
        entry_type_scope = data.get("entryTypeScope")  # Optional: "system", "workspace", or None

        if entry_type_scope == "system":
            # Explicitly use system type
            entry_types = self.repos.entry_types.multi_query({"slug": entry_type_slug, "group_id": None})
        elif entry_type_scope == "workspace":
            # Explicitly use workspace type
            entry_types = self.repos.entry_types.multi_query({"slug": entry_type_slug, "group_id": self.repos.group_id})
        else:
            # Auto-prefer: workspace type first, then system type
            entry_types = self.repos.entry_types.multi_query({"slug": entry_type_slug, "group_id": self.repos.group_id})
            if not entry_types:
                entry_types = self.repos.entry_types.multi_query({"slug": entry_type_slug})

        if not entry_types:
            scope_msg = f" (scope: {entry_type_scope})" if entry_type_scope else ""
            raise ValueError(f"Entry type not found: {entry_type_slug}{scope_msg}")

        entry_type = entry_types[0]

        # Create entry
        create_data = {
            "entry_type_id": entry_type.id,
            "title": data["title"],
            "slug": data["slug"],
            "status": data.get("status", "draft"),
            "summary": data.get("summary"),
            "description": data.get("description"),
            "data_json": data.get("data", {}),
            "metadata_json": data.get("metadataJson"),
            "publish_at": data.get("publishAt"),
            "expire_at": data.get("expireAt"),
        }

        entry = self.repos.entries.create(create_data)
        self.logger.info(f"Created entry: {data['slug']} (type: {entry_type_slug})")

        # Handle collection assignments
        collection_assignments = data.get("collections", [])
        if collection_assignments:
            self._assign_to_collections(entry.id, collection_assignments)

    def _assign_to_collections(self, entry_id: str, assignments: list[dict[str, Any]]) -> None:
        """Assign an entry to collections with order.

        Args:
            entry_id: UUID of the entry
            assignments: List of {slug: str, order: int} dicts
        """
        for assignment in assignments:
            collection_slug = assignment["slug"]
            order = assignment.get("order", 0)

            # Look up collection
            collections = self.repos.collections.multi_query({"slug": collection_slug})
            if not collections:
                self.logger.warning(f"Collection not found: {collection_slug}")
                continue

            collection = collections[0]

            # Create junction record
            try:
                # Use the EntryCollections model directly
                from marvin.db.models.platform import EntryCollections

                junction = EntryCollections(
                    entry_id=entry_id,
                    collection_id=collection.id,
                    sort_order=order,
                )
                self.repos.session.add(junction)
                self.repos.session.commit()
                self.logger.debug(f"Added to collection: {collection_slug} (order: {order})")
            except Exception as e:
                self.repos.session.rollback()
                self.logger.error(f"Failed to add to collection {collection_slug}: {e}")
