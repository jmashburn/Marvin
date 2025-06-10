"""
This module defines the SQLAlchemy model for group-specific webhooks.

It includes:
- `Method`: An enumeration for HTTP methods (GET, POST) supported by webhooks.
- `GroupWebhooksModel`: Represents a configured webhook for a group, including
  its URL, method, enabled status, and scheduling information.
"""

import enum
from datetime import UTC, datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Time, orm
from sqlalchemy.orm import Mapped, Session, mapped_column  # Added Session for __init__
from sqlalchemy.types import Enum as SqlAlchemyEnum  # Explicit import for sqlalchemy Enum type

from marvin.services.event_bus_service.event_types import EventDocumentType

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID
from .._model_utils.httpurl import HttpUrlType

if TYPE_CHECKING:
    from .groups import Groups


class Method(enum.Enum):
    """
    Enumeration for HTTP methods supported by webhooks.
    """

    GET = "GET"
    POST = "POST"


class GroupWebhooksModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a webhook configuration for a group.

    Webhooks can be used to send notifications or data to external URLs
    based on events or schedules.
    """

    __tablename__ = "webhook_urls"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the webhook configuration.")

    # Foreign key to the Groups model
    group_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("groups.id"), index=True, doc="ID of the group this webhook belongs to.")
    # Relationship to the parent Group
    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="webhooks", single_parent=True)

    enabled: Mapped[bool | None] = mapped_column(Boolean, default=False, doc="Indicates if this webhook is currently active. Defaults to False.")
    name: Mapped[str | None] = mapped_column(String, nullable=True, doc="User-defined name for this webhook (e.g., 'Notify Slack on Update').")
    url: Mapped[HttpUrlType] = mapped_column(
        HttpUrlType, nullable=False, doc="The URL to which the webhook request will be sent."
    )  # Made HttpUrlType non-optional as per nullable=False
    method: Mapped[Method] = mapped_column(
        SqlAlchemyEnum(Method),
        default=Method.POST,
        doc="HTTP method to use for the webhook request (GET or POST). Defaults to POST.",
    )  # Used SqlAlchemyEnum

    # New Fields for extended functionality
    webhook_type: Mapped[EventDocumentType | None] = mapped_column(
        SqlAlchemyEnum(EventDocumentType),
        default=EventDocumentType.generic,
        doc="Type of the webhook, influencing payload or trigger. Defaults to 'generic'.",
    )  # Used SqlAlchemyEnum and updated default
    scheduled_time: Mapped[time | None] = mapped_column(
        Time,
        default=lambda: datetime.now(UTC).time(),
        doc="Scheduled time (UTC) for the webhook to run, if it's a scheduled webhook. Defaults to current UTC time on creation.",
    )

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """
        Initializes a GroupWebhooksModel instance.

        Attributes are set by the `auto_init` decorator from `kwargs`.
        The `session` argument is required by `auto_init`.

        Args:
            session (Session): The SQLAlchemy session, required by `auto_init`.
            **kwargs: Attributes for the model, such as `name`, `url`, `method`, etc.
        """
        # All initialization is handled by auto_init based on kwargs.
        # Example:
        # webhook = GroupWebhooksModel(session=db_session, name="My Webhook", url="http://example.com/hook", group_id=group.id)
        pass  # Ellipsis (...) is a valid placeholder in Python, but pass is more conventional for empty blocks.
