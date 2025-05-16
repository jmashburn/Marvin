from pydantic import UUID4
from sqlalchemy.orm import Session

from ...repos._utils import NOT_SET, NotSet
from .webhook_factory import AllWebhooks


def get_webhooks(session: Session, *, group_id: UUID4 | None | NotSet = NOT_SET):
    return AllWebhooks(session, group_id=group_id)
