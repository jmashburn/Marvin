"""Collections repository."""

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform import Collections
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import CollectionRead, CollectionCreate, CollectionUpdate


class CollectionsRepository(GroupRepositoryGeneric):
    """Repository for managing collections."""

    def __init__(self, session: Session, group_id: UUID4) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Collections,
            schema=CollectionRead,
        )
        self._group_id = group_id
