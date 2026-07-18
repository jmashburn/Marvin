"""Abstract base for webhook type handlers."""

from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session


class BaseWebhook:
    session: Session
    _group_id: UUID4 | None = None

    def __init__(self, session: Session, group_id: UUID4 | None = None) -> None:
        self.session = session
        self._group_id = group_id

    @property
    def group_id(self) -> UUID4 | None:
        return self._group_id

    def info(self, webhook_config: Any, context: dict) -> dict:
        """Return the data dict for this webhook type's scheduled payload.

        Args:
            webhook_config: WebhookRead schema for the webhook being fired.
            context: Substitution context with timestamp, workspace_name,
                     workspace_slug, and trigger keys.
        """
        raise NotImplementedError
