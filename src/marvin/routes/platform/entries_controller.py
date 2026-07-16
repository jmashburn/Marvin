"""Entry routes."""

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError

from marvin.db.models.platform import EntryCollections
from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import CollectionRead, EntryCreate, EntryRead, EntryUpdate
from marvin.services.event_bus_service.event_types import EventEntryData, EventOperation, EventTypes

router = APIRouter(prefix="/entries")


@controller(router)
class EntriesController(BaseUserController):
    """Authenticated CRUD routes for entries."""

    def _resolve_entry_event_names(self, author_id) -> tuple[str | None, str | None]:
        """Return (workspace_name, author_name) for entry event payloads."""
        workspace_name = self.group.name if self.group else None
        author_name = None
        if author_id:
            if self.user and author_id == self.user.id:
                author_name = self.user.full_name
            else:
                author = self.repos.users.get_one(author_id)
                if author:
                    author_name = author.full_name
        return workspace_name, author_name

    @router.get("", response_model=list[EntryRead], summary="List Entries")
    def list_entries(self) -> list[EntryRead]:
        return self.repos.entries.get_all(order_by="created_at")

    @router.post("", response_model=EntryRead, status_code=status.HTTP_201_CREATED, summary="Create Entry")
    def create_entry(self, data: EntryCreate) -> EntryRead:
        # Inject created_by from authenticated user
        data_dict = data.model_dump()
        data_dict["created_by"] = self.user.id
        entry = self.repos.entries.create(data_dict)

        # Get entry type for event
        entry_type_slug = None
        if entry.entry_type_id:
            entry_type = self.repos.entry_types.get_one(entry.entry_type_id)
            if entry_type:
                entry_type_slug = entry_type.slug

        # Emit event
        try:
            workspace_name, author_name = self._resolve_entry_event_names(entry.created_by)
            self.event_bus.dispatch(
                integration_id="entry_management",
                group_id=self.group_id,
                event_type=EventTypes.entry_created,
                document_data=EventEntryData(
                    operation=EventOperation.create,
                    entry_id=entry.id,
                    entry_title=entry.title,
                    entry_type=entry_type_slug,
                    workspace_id=entry.group_id,
                    workspace_name=workspace_name,
                    author_id=entry.created_by,
                    author_name=author_name,
                ),
                message=f"Entry '{entry.title}' created",
                user_id=self.user.id if self.user else None,
                entity_id=entry.id,
                entity_type="entry",
            )
        except Exception as e:
            # Log error but don't fail the request
            self.logger.error(f"Failed to dispatch entry_created event: {e}", exc_info=True)

        return entry

    @router.get("/{item_id}", response_model=EntryRead, summary="Get Entry")
    def get_entry(self, item_id: UUID4) -> EntryRead:
        entry = self.repos.entries.get_one(item_id)
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        return entry

    @router.patch("/{item_id}", response_model=EntryRead, summary="Update Entry")
    def update_entry(self, item_id: UUID4, data: EntryUpdate) -> EntryRead:
        old_entry = self.repos.entries.get_one(item_id)
        if not old_entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")

        entry = self.repos.entries.update(item_id, data)

        # Get entry type for event
        entry_type_slug = None
        if entry.entry_type_id:
            entry_type = self.repos.entry_types.get_one(entry.entry_type_id)
            if entry_type:
                entry_type_slug = entry_type.slug

        # Emit update event
        try:
            workspace_name, author_name = self._resolve_entry_event_names(entry.created_by)
            self.event_bus.dispatch(
                integration_id="entry_management",
                group_id=self.group_id,
                event_type=EventTypes.entry_updated,
                document_data=EventEntryData(
                    operation=EventOperation.update,
                    entry_id=entry.id,
                    entry_title=entry.title,
                    entry_type=entry_type_slug,
                    workspace_id=entry.group_id,
                    workspace_name=workspace_name,
                    author_id=entry.created_by,
                    author_name=author_name,
                ),
                message=f"Entry '{entry.title}' updated",
                user_id=self.user.id if self.user else None,
                entity_id=entry.id,
                entity_type="entry",
            )
        except Exception as e:
            self.logger.error(f"Failed to dispatch entry_updated event: {e}", exc_info=True)

        # Emit status change events if status changed
        if old_entry.status != entry.status:
            try:
                workspace_name, author_name = self._resolve_entry_event_names(entry.created_by)
                if entry.status == "published":
                    self.event_bus.dispatch(
                        integration_id="entry_management",
                        group_id=self.group_id,
                        event_type=EventTypes.entry_published,
                        document_data=EventEntryData(
                            operation=EventOperation.update,
                            entry_id=entry.id,
                            entry_title=entry.title,
                            entry_type=entry_type_slug,
                            workspace_id=entry.group_id,
                            workspace_name=workspace_name,
                            author_id=entry.created_by,
                            author_name=author_name,
                        ),
                        message=f"Entry '{entry.title}' published",
                        user_id=self.user.id if self.user else None,
                        entity_id=entry.id,
                        entity_type="entry",
                    )
                elif old_entry.status == "published":
                    self.event_bus.dispatch(
                        integration_id="entry_management",
                        group_id=self.group_id,
                        event_type=EventTypes.entry_unpublished,
                        document_data=EventEntryData(
                            operation=EventOperation.update,
                            entry_id=entry.id,
                            entry_title=entry.title,
                            entry_type=entry_type_slug,
                            workspace_id=entry.group_id,
                            workspace_name=workspace_name,
                            author_id=entry.created_by,
                            author_name=author_name,
                        ),
                        message=f"Entry '{entry.title}' unpublished",
                        user_id=self.user.id if self.user else None,
                        entity_id=entry.id,
                        entity_type="entry",
                    )

                # Handle archived status
                if entry.status == "archived":
                    self.event_bus.dispatch(
                        integration_id="entry_management",
                        group_id=self.group_id,
                        event_type=EventTypes.entry_archived,
                        document_data=EventEntryData(
                            operation=EventOperation.update,
                            entry_id=entry.id,
                            entry_title=entry.title,
                            entry_type=entry_type_slug,
                            workspace_id=entry.group_id,
                            workspace_name=workspace_name,
                            author_id=entry.created_by,
                            author_name=author_name,
                        ),
                        message=f"Entry '{entry.title}' archived",
                        user_id=self.user.id if self.user else None,
                        entity_id=entry.id,
                        entity_type="entry",
                    )
                elif old_entry.status == "archived":
                    self.event_bus.dispatch(
                        integration_id="entry_management",
                        group_id=self.group_id,
                        event_type=EventTypes.entry_restored,
                        document_data=EventEntryData(
                            operation=EventOperation.update,
                            entry_id=entry.id,
                            entry_title=entry.title,
                            entry_type=entry_type_slug,
                            workspace_id=entry.group_id,
                            workspace_name=workspace_name,
                            author_id=entry.created_by,
                            author_name=author_name,
                        ),
                        message=f"Entry '{entry.title}' restored from archive",
                        user_id=self.user.id if self.user else None,
                        entity_id=entry.id,
                        entity_type="entry",
                    )
            except Exception as e:
                self.logger.error(f"Failed to dispatch entry status change event: {e}", exc_info=True)

        return entry

    @router.delete("/{item_id}", summary="Delete Entry")
    def delete_entry(self, item_id: UUID4) -> dict:
        entry = self.repos.entries.get_one(item_id)
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")

        # Get entry type for event
        entry_type_slug = None
        if entry.entry_type_id:
            entry_type = self.repos.entry_types.get_one(entry.entry_type_id)
            if entry_type:
                entry_type_slug = entry_type.slug

        # Emit event before deletion
        try:
            workspace_name, author_name = self._resolve_entry_event_names(entry.created_by)
            self.event_bus.dispatch(
                integration_id="entry_management",
                group_id=self.group_id,
                event_type=EventTypes.entry_deleted,
                document_data=EventEntryData(
                    operation=EventOperation.delete,
                    entry_id=entry.id,
                    entry_title=entry.title,
                    entry_type=entry_type_slug,
                    workspace_id=entry.group_id,
                    workspace_name=workspace_name,
                    author_id=entry.created_by,
                    author_name=author_name,
                ),
                message=f"Entry '{entry.title}' deleted",
                user_id=self.user.id if self.user else None,
                entity_id=entry.id,
                entity_type="entry",
            )
        except Exception as e:
            self.logger.error(f"Failed to dispatch entry_deleted event: {e}", exc_info=True)

        self.repos.entries.delete(item_id)
        return {"status": "ok", "message": "Entry deleted successfully"}

    @router.get("/{entry_id}/collections", response_model=list[CollectionRead], summary="List Entry Collections")
    def list_entry_collections(self, entry_id: UUID4) -> list[CollectionRead]:
        """Get all collections this entry belongs to."""
        entry = self.repos.entries.get_one(entry_id)
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")

        # Query collections via junction table
        collection_ids = self.session.query(EntryCollections.collection_id).filter(EntryCollections.entry_id == entry_id).all()
        collection_ids = [cid[0] for cid in collection_ids]

        if not collection_ids:
            return []

        return [collection for collection in self.repos.collections.get_all() if collection.id in collection_ids]

    @router.post("/{entry_id}/collections/{collection_id}", status_code=status.HTTP_201_CREATED, summary="Add Entry to Collection")
    def add_entry_to_collection(self, entry_id: UUID4, collection_id: UUID4) -> dict:
        """Add an entry to a collection."""
        # Verify entry exists
        entry = self.repos.entries.get_one(entry_id)
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")

        # Verify collection exists and belongs to same group
        collection = self.repos.collections.get_one(collection_id)
        if not collection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")

        if collection.group_id != entry.group_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Entry and collection must belong to the same workspace.")

        # Check if already exists
        existing = (
            self.session.query(EntryCollections)
            .filter(EntryCollections.entry_id == entry_id, EntryCollections.collection_id == collection_id)
            .first()
        )

        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Entry is already in this collection.")

        # Get max sort_order for this collection
        max_sort_order = (
            self.session.query(sa.func.max(EntryCollections.sort_order)).filter(EntryCollections.collection_id == collection_id).scalar()
        ) or -1

        # Create junction record
        junction = EntryCollections(entry_id=entry_id, collection_id=collection_id, sort_order=max_sort_order + 1)
        self.session.add(junction)
        self.session.commit()

        # Get entry type for event
        entry_type_slug = None
        if entry.entry_type_id:
            entry_type = self.repos.entry_types.get_one(entry.entry_type_id)
            if entry_type:
                entry_type_slug = entry_type.slug

        # Emit event
        self.event_bus.dispatch(
            integration_id="entry_management",
            group_id=self.group_id,
            event_type=EventTypes.entry_added_to_collection,
            document_data=EventEntryData(
                operation=EventOperation.update,
                entry_id=entry.id,
                entry_title=entry.title,
                entry_type=entry_type_slug,
                workspace_id=entry.group_id,
                author_id=entry.created_by,
            ),
            message=f"Entry '{entry.title}' added to collection '{collection.name}'",
            user_id=self.user.id if self.user else None,
            entity_id=entry.id,
            entity_type="entry",
        )

        return {"message": "Entry added to collection successfully"}

    @router.delete("/{entry_id}/collections/{collection_id}", summary="Remove Entry from Collection")
    def remove_entry_from_collection(self, entry_id: UUID4, collection_id: UUID4) -> dict:
        """Remove an entry from a collection."""
        # Get entry and collection before deletion for event
        entry = self.repos.entries.get_one(entry_id)
        collection = self.repos.collections.get_one(collection_id)

        # Delete junction record
        deleted = (
            self.session.query(EntryCollections)
            .filter(EntryCollections.entry_id == entry_id, EntryCollections.collection_id == collection_id)
            .delete()
        )

        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry is not in this collection.")

        self.session.commit()

        # Emit event if we have entry data
        if entry:
            # Get entry type for event
            entry_type_slug = None
            if entry.entry_type_id:
                entry_type = self.repos.entry_types.get_one(entry.entry_type_id)
                if entry_type:
                    entry_type_slug = entry_type.slug

            self.event_bus.dispatch(
                integration_id="entry_management",
                group_id=self.group_id,
                event_type=EventTypes.entry_removed_from_collection,
                document_data=EventEntryData(
                    operation=EventOperation.update,
                    entry_id=entry.id,
                    entry_title=entry.title,
                    entry_type=entry_type_slug,
                    workspace_id=entry.group_id,
                    author_id=entry.created_by,
                ),
                message=f"Entry '{entry.title}' removed from collection '{collection.name if collection else collection_id}'",
                user_id=self.user.id if self.user else None,
                entity_id=entry.id,
                entity_type="entry",
            )

        return {"status": "ok", "message": "Entry removed from collection successfully"}
