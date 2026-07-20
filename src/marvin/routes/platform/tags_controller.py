"""Tag routes — CRUD over the workspace's shared tag vocabulary, plus entry attach/detach.

``POST /tags`` is find-or-create by slug (see ``TagsRepository``), so the UI can resolve a
freshly typed tag name to a stable id in one call. Attach/detach are lightweight and emit no
events — tags are labels, not curated placements like collections.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4
from sqlalchemy import func

from marvin.db.models.platform import EntryTags, Tags
from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import TagCreate, TagRead, TagUpdate

router = APIRouter(prefix="/tags")


@controller(router)
class TagsController(BaseUserController):
    """Authenticated CRUD routes for tags."""

    @router.get("", response_model=list[TagRead], summary="List Tags")
    def list_tags(self) -> list[TagRead]:
        tags = self.repos.tags.get_all(order_by="name", order_descending=False)

        # Attach entry counts in one grouped query (avoids N+1).
        counts = dict(
            self.session.query(EntryTags.tag_id, func.count(EntryTags.entry_id))
            .join(Tags, Tags.id == EntryTags.tag_id)
            .filter(Tags.group_id == self.group_id)
            .group_by(EntryTags.tag_id)
            .all()
        )
        for tag in tags:
            tag.entry_count = counts.get(tag.id, 0)
        return tags

    @router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED, summary="Create Tag")
    def create_tag(self, data: TagCreate) -> TagRead:
        """Find-or-create a tag by slug. Returns the existing tag if the name already resolves to one."""
        return self.repos.tags.create(data)

    @router.get("/{item_id}", response_model=TagRead, summary="Get Tag")
    def get_tag(self, item_id: UUID4) -> TagRead:
        tag = self.repos.tags.get_one(item_id)
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
        return tag

    @router.patch("/{item_id}", response_model=TagRead, summary="Update Tag")
    def update_tag(self, item_id: UUID4, data: TagUpdate) -> TagRead:
        if not self.repos.tags.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
        return self.repos.tags.update(item_id, data)

    @router.delete("/{item_id}", summary="Delete Tag")
    def delete_tag(self, item_id: UUID4) -> dict:
        if not self.repos.tags.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
        # FK cascade on entry_tags clears the junction rows; deleting a tag just unlabels entries.
        self.repos.tags.delete(item_id)
        return {"status": "ok", "message": "Tag deleted successfully"}

    @router.post("/{tag_id}/entries/{entry_id}", status_code=status.HTTP_201_CREATED, summary="Attach Tag to Entry")
    def attach_tag(self, tag_id: UUID4, entry_id: UUID4) -> dict:
        """Apply a tag to an entry. Idempotent — re-attaching an existing pair is a no-op."""
        tag = self.repos.tags.get_one(tag_id)
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
        entry = self.repos.entries.get_one(entry_id)
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        if entry.group_id != tag.group_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Entry and tag must belong to the same workspace.")

        existing = self.session.query(EntryTags).filter(EntryTags.entry_id == entry_id, EntryTags.tag_id == tag_id).first()
        if existing is None:
            self.session.add(EntryTags(entry_id=entry_id, tag_id=tag_id))
            self.session.commit()
            self._resync_smart_membership(entry_id)
        return {"status": "ok", "message": "Tag attached"}

    @router.delete("/{tag_id}/entries/{entry_id}", summary="Detach Tag from Entry")
    def detach_tag(self, tag_id: UUID4, entry_id: UUID4) -> dict:
        deleted = self.session.query(EntryTags).filter(EntryTags.entry_id == entry_id, EntryTags.tag_id == tag_id).delete()
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry does not carry this tag.")
        self.session.commit()
        self._resync_smart_membership(entry_id)
        return {"status": "ok", "message": "Tag detached"}

    def _resync_smart_membership(self, entry_id: UUID4) -> None:
        """A tag change can flip a tag-based smart collection's membership — re-materialize it."""
        from marvin.db.models.platform import Entries
        from marvin.services.collections.smart_collections import sync_entry

        entry = self.session.get(Entries, entry_id)
        if entry and sync_entry(self.session, entry.group_id, entry):
            self.session.commit()
