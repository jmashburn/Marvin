"""Resources repository."""

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform import Resources
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import ResourceRead


class ResourcesRepository(GroupRepositoryGeneric):
    """Repository for managing resources."""

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Resources,
            schema=ResourceRead,
            group_id=group_id,
        )
