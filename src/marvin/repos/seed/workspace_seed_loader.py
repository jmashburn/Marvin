"""Complete workspace seed loader for importing workspace data from JSON."""

import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from marvin.core.root_logger import get_logger
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

    def __init__(self, repos: AllRepositories, logger=None):
        """Initialize loader with repository access.

        Args:
            repos: Repository factory for database operations
            logger: Optional logger instance
        """
        self.repos = repos
        self.logger = logger or get_logger(__name__)

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

        return self._load_data(data, zip_file=None)

    def load_seed_zip(self, zip_path: Path) -> dict[str, int]:
        """Load a workspace seed bundle from a zip file (JSON + asset binaries).

        Args:
            zip_path: Path to workspace bundle zip file

        Returns:
            Dictionary with counts by type
        """
        self.logger.info(f"Loading workspace bundle from: {zip_path}")

        with zipfile.ZipFile(zip_path, "r") as zf:
            with zf.open("workspace-export.json") as f:
                data = json.load(f)

            return self._load_data(data, zip_file=zf)

    def _load_data(self, data: dict[str, Any], zip_file: zipfile.ZipFile | None = None) -> dict[str, int]:
        """Load workspace data from a parsed dict, optionally extracting asset binaries from a zip.

        Args:
            data: Parsed workspace seed dict
            zip_file: Open ZipFile for binary extraction, or None for metadata-only

        Returns:
            Dictionary with counts by type
        """
        results = {
            "collections": 0,
            "entry_types": 0,
            "entries": 0,
            "resources": 0,
            "assets": 0,
            "errors": 0,
        }

        # 0. Create or find workspace from seed data
        workspace_data = data.get("workspace")
        workspace = None
        if workspace_data:
            workspace = self._ensure_workspace(workspace_data)
            from marvin.repos.all_repositories import get_repositories

            self.repos = get_repositories(self.repos.session, group_id=workspace.id)
            self.logger.info(f"Using workspace: {workspace.name} ({workspace.slug})")

            site_data = data.get("site")
            if site_data:
                self._update_site_preferences(site_data)

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

        # 3. Resources (before entries so entry-resource links can resolve)
        resources_data = data.get("resources", [])
        if resources_data:
            self.logger.info(f"Creating {len(resources_data)} resources...")
            for res_data in resources_data:
                try:
                    self._create_resource(res_data)
                    results["resources"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to create resource {res_data.get('slug')}: {e}")
                    results["errors"] += 1

        # 4. Assets (before entries so entry-asset links can resolve)
        assets_data = data.get("assets", [])
        if assets_data:
            self.logger.info(f"Importing {len(assets_data)} assets...")
            results["assets"] = self._import_assets(assets_data, zip_file)

        # 5. Entries
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
            f"{results['resources']} resources, "
            f"{results['assets']} assets, "
            f"{results['errors']} errors"
        )

        # 6. Send owner invitation emails if provided
        if workspace_data and workspace:
            owner_emails = []
            if workspace_data.get("ownerEmail"):
                owner_emails.append(workspace_data["ownerEmail"])
            if workspace_data.get("ownerEmails"):
                owner_emails.extend(workspace_data["ownerEmails"])

            for owner_email in owner_emails:
                try:
                    self._send_owner_invitation(owner_email, workspace)
                except Exception as e:
                    self.logger.error(f"Failed to send owner invitation to {owner_email}: {e}")
                    results["errors"] += 1

        return results

    def _import_assets(self, assets_data: list[dict[str, Any]], zip_file: zipfile.ZipFile | None) -> int:
        """Import assets, uploading binaries from zip if available.

        Args:
            assets_data: List of asset metadata dicts from seed
            zip_file: Open ZipFile containing binaries under files/, or None

        Returns:
            Count of assets imported
        """
        from datetime import datetime

        from marvin.services.assets.asset_storage_service import AssetStorageService
        from marvin.services.storage.provider_factory import get_storage_provider

        storage_provider = get_storage_provider()
        zip_names = set(zip_file.namelist()) if zip_file else set()
        workspace = self.repos.groups.get_one(self.repos.group_id)
        workspace_slug = workspace.slug if workspace else "workspace"
        user_id = self._get_seed_user_id()
        count = 0

        for asset in assets_data:
            slug = asset["slug"]

            existing = self.repos.assets.multi_query({"slug": slug})
            if existing:
                self.logger.debug(f"Asset already exists: {slug}")
                continue

            zip_path = f"files/{asset['storageKey']}"
            has_binary = zip_file is not None and zip_path in zip_names

            if has_binary:
                try:
                    binary_data = BytesIO(zip_file.read(zip_path))

                    storage_service = AssetStorageService(self.repos, storage_provider)
                    new_storage_key = storage_service.generate_storage_key(
                        workspace_slug=workspace_slug,
                        filename=asset.get("originalFilename") or f"{slug}.{asset.get('extension', 'bin')}",
                        upload_date=datetime.now(),
                    )

                    storage_provider.put(new_storage_key, binary_data, asset.get("mimeType", "application/octet-stream"))
                    new_public_url = storage_provider.get_public_url(new_storage_key)
                except Exception as e:
                    self.logger.error(f"Failed to store binary for asset {slug}: {e}")
                    continue
            else:
                if zip_file is not None:
                    self.logger.warning(f"Asset binary not found in bundle, skipping: {slug}")
                new_storage_key = asset.get("storageKey", "")
                new_public_url = asset.get("publicUrl", "")

            if not user_id:
                self.logger.warning(f"No user found for asset creation, skipping: {slug}")
                continue

            create_data = {
                "group_id": self.repos.group_id,
                "slug": slug,
                "name": asset.get("name", slug),
                "original_filename": asset.get("originalFilename"),
                "extension": asset.get("extension"),
                "file_size": asset.get("fileSize"),
                "mime_type": asset.get("mimeType"),
                "asset_type": asset.get("assetType"),
                "storage_provider": asset.get("storageProvider", "local"),
                "storage_key": new_storage_key,
                "public_url": new_public_url,
                "alt_text": asset.get("altText"),
                "description": asset.get("description"),
                "width": asset.get("width"),
                "height": asset.get("height"),
                "metadata_json": asset.get("metadataJson"),
                "uploaded_by": user_id,
            }
            create_data = {k: v for k, v in create_data.items() if v is not None}

            try:
                self.repos.assets.create(create_data)
                self.logger.info(f"Imported asset: {slug}")
                count += 1
            except Exception as e:
                self.logger.error(f"Failed to create asset record {slug}: {e}")

        return count

    def _ensure_workspace(self, data: dict[str, Any]):
        """Create workspace if it doesn't exist, or return existing one.

        Args:
            data: Workspace data from seed file

        Returns:
            GroupRead: The workspace/group
        """
        from marvin.schemas.group.group import GroupCreate
        from marvin.services.group.group_service import GroupService

        # Check if workspace exists by slug (if provided) or by name
        existing_groups = None

        if data.get("slug"):
            # Try to find by slug first
            existing_groups = self.repos.groups.multi_query({"slug": data["slug"]})
            if existing_groups:
                self.logger.info(f"Workspace found by slug: {data['slug']}")
                return existing_groups[0]

        # If no slug or slug not found, try to find by name
        existing_groups = self.repos.groups.multi_query({"name": data["name"]})
        if existing_groups:
            self.logger.info(f"Workspace found by name: {data['name']}")
            return existing_groups[0]

        # Create new workspace if not found
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
            # Use multi_query to find by group_id, then update by group_id (not id)
            prefs_list = self.repos.group_preferences.multi_query({"group_id": self.repos.group_id})
            if prefs_list:
                # Update using group_id as the match key
                self.repos.group_preferences.update(self.repos.group_id, update_data, match_key="group_id")
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

        # Handle resource assignments
        resource_assignments = data.get("resources", [])
        if resource_assignments:
            self._assign_to_resources(entry.id, resource_assignments)

    def _get_seed_user_id(self) -> str | None:
        """Get a user ID for seed-created records.

        Returns the first admin user's ID, or the first user if no admin exists.
        """
        if hasattr(self, "_seed_user_id"):
            return self._seed_user_id

        from marvin.db.models.users import Users

        admin = self.repos.session.query(Users).filter(Users.admin == True).first()  # noqa: E712
        if admin:
            self._seed_user_id = admin.id
            return self._seed_user_id

        user = self.repos.session.query(Users).first()
        self._seed_user_id = user.id if user else None
        return self._seed_user_id

    def _create_resource(self, data: dict[str, Any]) -> None:
        """Create a resource if it doesn't exist.

        Args:
            data: Resource data from seed file
        """
        existing = self.repos.resources.multi_query({"slug": data["slug"]})
        if existing:
            self.logger.debug(f"Resource already exists: {data['slug']}")
            return

        user_id = self._get_seed_user_id()
        if not user_id:
            self.logger.warning(f"No user found for resource creation, skipping: {data['slug']}")
            return

        create_data = {
            "group_id": self.repos.group_id,
            "name": data["name"],
            "slug": data["slug"],
            "resource_type": data.get("resourceType", "material"),
            "description": data.get("description"),
            "url": data.get("url"),
            "metadata_json": data.get("metadataJson"),
            "created_by": user_id,
        }

        self.repos.resources.create(create_data)
        self.logger.info(f"Created resource: {data['slug']}")

    def _assign_to_resources(self, entry_id: str, assignments: list[dict[str, Any]]) -> None:
        """Link an entry to resources with role and position.

        Args:
            entry_id: UUID of the entry
            assignments: List of {slug: str, role?: str, position?: int} dicts
        """
        for assignment in assignments:
            resource_slug = assignment["slug"]
            role = assignment.get("role")
            position = assignment.get("position", 0)

            resources = self.repos.resources.multi_query({"slug": resource_slug})
            if not resources:
                self.logger.warning(f"Resource not found: {resource_slug}")
                continue

            resource = resources[0]

            try:
                from marvin.db.models.platform import EntryResources

                junction = EntryResources(
                    entry_id=entry_id,
                    resource_id=resource.id,
                    role=role,
                    position=position,
                )
                self.repos.session.add(junction)
                self.repos.session.commit()
                self.logger.debug(f"Linked resource: {resource_slug} (role: {role})")
            except Exception as e:
                self.repos.session.rollback()
                self.logger.error(f"Failed to link resource {resource_slug}: {e}")

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

    def _send_owner_invitation(self, owner_email: str, workspace) -> None:
        """Create an owner-level invitation token and send it via email.

        Args:
            owner_email: Email address to send the invitation to
            workspace: The workspace GroupRead object
        """
        from marvin.core.config import get_app_settings
        from marvin.core.security import url_safe_token
        from marvin.schemas.group.invite_token import InviteTokenSave
        from marvin.schemas.mapper import cast
        from marvin.services.email.email_service import EmailService

        settings = get_app_settings()

        # Check if SMTP is enabled
        if not settings.SMTP_ENABLED:
            self.logger.warning(f"SMTP not enabled - cannot send owner invitation to {owner_email}")
            self.logger.info(f"Owner invitation token should be created manually for: {owner_email}")
            return

        # Create an owner-level invitation token with unlimited uses
        token_data = InviteTokenSave(
            token=url_safe_token(),
            group_id=self.repos.group_id,
            uses_left=-1,  # Unlimited uses for owner
            workspace_role="OWNER",
        )

        created_token = self.repos.group_invite_tokens.create(token_data)
        self.logger.info(f"Created owner invitation token for {owner_email}: {created_token.token}")

        # Construct registration URL
        registration_url = f"{settings.BASE_URL}/register?token={created_token.token}"

        # ALWAYS display the registration URL in logs (in case email fails)
        self.logger.info("=" * 80)
        self.logger.info(f"OWNER INVITATION LINK: {registration_url}")
        self.logger.info(f"Recipient: {owner_email}")
        self.logger.info(f"Token: {created_token.token}")
        self.logger.info("=" * 80)

        # Send invitation email
        try:
            email_service = EmailService()
            success = email_service.send_invitation(
                recipient_address=owner_email,
                invitation_url=registration_url,
                group_id=str(self.repos.group_id) if self.repos.group_id else None,
            )

            if success:
                self.logger.info(f"✓ Owner invitation email sent to {owner_email}")
            else:
                self.logger.warning(f"✗ Failed to send owner invitation email to {owner_email}")
                self.logger.warning(f"Please share the registration link manually (see above)")
        except Exception as e:
            self.logger.error(f"✗ Error sending owner invitation email: {e}")
            self.logger.warning(f"Please share the registration link manually (see above)")
