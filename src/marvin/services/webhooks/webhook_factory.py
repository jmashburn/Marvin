"""Factory providing access to all webhook type handlers."""

from functools import cached_property

from pydantic import UUID4
from sqlalchemy.orm import Session

from ...repos._utils import NOT_SET, NotSet
from .base_webhook import BaseWebhook
from .entries import EntriesWebhook
from .generic import GenericWebhook
from .user import UserWebhook


class AllWebhooks:
    """Registry and factory for webhook type handlers."""

    session: Session
    group_id: UUID4 | None | NotSet

    def __init__(self, session: Session, *, group_id: UUID4 | None | NotSet = NOT_SET) -> None:
        self.session = session
        self.group_id = group_id

    def get_webhook_handler(self, webhook_type_name: str) -> BaseWebhook | None:
        """Return the handler for the given type name, or None if unknown."""
        if hasattr(self, webhook_type_name):
            handler = getattr(self, webhook_type_name)
            if isinstance(handler, BaseWebhook):
                return handler
        return None

    def _effective_group_id(self) -> UUID4 | None:
        return None if self.group_id is NOT_SET else self.group_id  # type: ignore[return-value]

    @cached_property
    def generic(self) -> GenericWebhook:
        return GenericWebhook(self.session, group_id=self._effective_group_id())

    @cached_property
    def user(self) -> UserWebhook:
        return UserWebhook(self.session, group_id=self._effective_group_id())

    @cached_property
    def entries(self) -> EntriesWebhook:
        return EntriesWebhook(self.session, group_id=self._effective_group_id())
