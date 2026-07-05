"""Entry type routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.platform import EntryTypeCreate, EntryTypeRead, EntryTypeUpdate

router = APIRouter(prefix="/entry-types")


@controller(router)
class EntryTypesController(BaseUserController):
    """Authenticated CRUD routes for entry types."""

    @router.get("", response_model=list[EntryTypeRead], summary="List Entry Types")
    def list_entry_types(self) -> list[EntryTypeRead]:
        return self.repos.entry_types.get_all(order_by="sort_order", order_descending=False)

    @router.post("", response_model=EntryTypeRead, status_code=status.HTTP_201_CREATED, summary="Create Entry Type")
    def create_entry_type(self, data: EntryTypeCreate) -> EntryTypeRead:
        return self.repos.entry_types.create(data)

    @router.get("/{item_id}", response_model=EntryTypeRead, summary="Get Entry Type")
    def get_entry_type(self, item_id: UUID4) -> EntryTypeRead:
        entry_type = self.repos.entry_types.get_one(item_id)
        if not entry_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry type not found.")
        return entry_type

    @router.patch("/{item_id}", response_model=EntryTypeRead, summary="Update Entry Type")
    def update_entry_type(self, item_id: UUID4, data: EntryTypeUpdate) -> EntryTypeRead:
        if not self.repos.entry_types.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry type not found.")
        return self.repos.entry_types.update(item_id, data)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Entry Type")
    def delete_entry_type(self, item_id: UUID4) -> None:
        if not self.repos.entry_types.get_one(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry type not found.")
        self.repos.entry_types.delete(item_id)
