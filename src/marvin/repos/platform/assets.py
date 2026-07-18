"""Assets repository."""

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform import Assets
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import AssetRead


class AssetsRepository(GroupRepositoryGeneric):
    """Repository for managing assets."""

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Assets,
            schema=AssetRead,
            group_id=group_id,
        )
