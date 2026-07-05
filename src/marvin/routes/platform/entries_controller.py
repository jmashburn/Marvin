"""Entry routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import EntryCreate, EntryRead, EntryUpdate

router = APIRouter(prefix="/entries")


@controller(router)
class EntriesController(BaseUserController):
    """Authenticated CRUD routes for entries."""

    @router.get("", response_model=list[EntryRead], summary="List Entries")
    def list_entries(self) -> list[EntryRead]:
        return self.repos.entries.get_all(order_by="created_at")

    @router.post("", response_model=EntryRead, status_code=status.HTTP_201_CREATED, summary="Create Entry")
    def create_entry(self, data: EntryCreate) -> EntryRead:
        return self.repos.entries.create(data)

    @router.get("/{item_id}", response_model=EntryRead, summary="Get Entry")
    def get_entry(self, item_id: UUID4) -> EntryRead:
        entry = self.repos.entries.get_one(item_id)
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        return entry

    @router.patch("/{item_id}", response_model=EntryRead, summary="Update Entry")
    def update_entry(self, item_id: UUID4, data: EntryUpdate) -> EntryRead:
        if not self.repos.entries.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        return self.repos.entries.update(item_id, data)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Entry")
    def delete_entry(self, item_id: UUID4) -> None:
        if not self.repos.entries.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
        self.repos.entries.delete(item_id)
