"""Site Clients repository."""

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform import SiteClients
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import SiteClientRead, SiteClientCreate, SiteClientUpdate


class SiteClientsRepository(GroupRepositoryGeneric):
    """Repository for managing site clients."""

    def __init__(self, session: Session, group_id: UUID4) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=SiteClients,
            schema=SiteClientRead,
        )
        self._group_id = group_id
