"""Entry routes."""

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError

from marvin.db.models.platform import EntryCollections
from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import CollectionRead, EntryCreate, EntryRead, EntryUpdate
from marvin.services.entries import EntryService
from marvin.services.event_bus_service.event_types import EventEntryData, EventOperation, EventTypes

router = APIRouter(prefix="/entries")


@controller(router)
class EntriesController(BaseUserController):
    """Authenticated CRUD routes for entries. Entry mutation + its events live in EntryService;
    this controller owns the HTTP concerns (auth, 404s, response shape)."""

    def _entries(self) -> EntryService:
        """The entry domain service, wired with this request's actor + event bus."""
        return EntryService(
            self.session, self.group_id,
            event_bus=self.event_bus,
            actor_id=self.user.id if self.user else None,
        )

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
        data_dict = data.model_dump()
        data_dict["created_by"] = self.user.id  # inject the authenticated author
        return self._entries().create(data_dict)

    @router.get("/{item_id}", response_model=EntryRead, summary="Get Entry")
    def get_entry(self, item_id: UUID4) -> EntryRead:
        entry = self.repos.entries.get_one(item_id)
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        return entry

    @router.post("/{item_id}/apply-suggestion", response_model=EntryRead, summary="Apply AI Suggestion")
    def apply_suggestion(self, item_id: UUID4) -> EntryRead:
        """Apply the entry's staged AI suggestion (suggestion_json) and clear it.

        This is the human-approval half of write-back: an AI op stages proposed changes under
        suggestion_json (when approval_mode doesn't auto-apply); this endpoint commits them.
        """
        if not self.repos.entries.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        return self._entries().apply_suggestion(item_id)

    @router.post("/{item_id}/reject-suggestion", response_model=EntryRead, summary="Reject AI Suggestion")
    def reject_suggestion(self, item_id: UUID4) -> EntryRead:
        """Discard the entry's staged AI suggestion without applying it."""
        existing = self.repos.entries.get_one(item_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        return self.repos.entries.clear_suggestion(item_id)

    @router.patch("/{item_id}", response_model=EntryRead, summary="Update Entry")
    def update_entry(self, item_id: UUID4, data: EntryUpdate) -> EntryRead:
        # The service emits entry_updated + any status-transition events (published/unpublished/
        # archived/restored), in that order.
        entry = self._entries().update(item_id, data)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        return entry

    @router.delete("/{item_id}", summary="Delete Entry")
    def delete_entry(self, item_id: UUID4) -> dict:
        if not self._entries().delete(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
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
        workspace_name, author_name = self._resolve_entry_event_names(entry.created_by)
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
                workspace_name=workspace_name,
                author_id=entry.created_by,
                author_name=author_name,
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

            workspace_name, author_name = self._resolve_entry_event_names(entry.created_by)
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
                    workspace_name=workspace_name,
                    author_id=entry.created_by,
                    author_name=author_name,
                ),
                message=f"Entry '{entry.title}' removed from collection '{collection.name if collection else collection_id}'",
                user_id=self.user.id if self.user else None,
                entity_id=entry.id,
                entity_type="entry",
            )

        return {"status": "ok", "message": "Entry removed from collection successfully"}
