from pydantic import UUID4

from sqlalchemy.orm import Session

from .repository_factory import AllRepositories
from ._utils import NotSet, NOT_SET


def get_repositories(session: Session, *, group_id: UUID4 | None | NotSet = NOT_SET):
    return AllRepositories(session, group_id=group_id)
