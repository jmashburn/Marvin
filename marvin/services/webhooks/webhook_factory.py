from functools import cached_property

from pydantic import UUID4
from sqlalchemy.orm import Session


from .generic import GenericWebhook
from .user import UserWebhook
from ...repos._utils import NOT_SET, NotSet


class AllWebhooks:
    """
    `AllWebhooks` class is the data access layer for all actions within
    marvin. Database uses composition from classes derived from AccessModel. These
    can be substantiated from the AccessModel class or through inheritance when
    additional methods are required.
    """

    def __init__(
        self,
        session: Session,
        *,
        group_id: UUID4 | None | NotSet = NOT_SET,
    ) -> None:
        self.session = session
        self.group_id = group_id

    @classmethod
    def get_webhook(self, webhook_type: str):
        return getattr(self, str(webhook_type))

    @cached_property
    def generic(self) -> GenericWebhook:
        return GenericWebhook(self.session, self.group_id)

    @cached_property
    def user(self) -> UserWebhook:
        return UserWebhook(self.session, self.group_id)
