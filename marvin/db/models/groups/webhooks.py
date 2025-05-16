import enum
from datetime import datetime, time, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Time, orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID
from .._model_utils.httpurl import HttpUrlType
from ....services.event_bus_service.event_types import EventDocumentType

if TYPE_CHECKING:
    from .groups import Groups


class Method(enum.Enum):
    GET = "GET"
    POST = "POST"


# PUT = "PUT"
# DELETE = "DELETE"


class GroupWebhooksModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "webhook_urls"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="webhooks", single_parent=True)
    group_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("groups.id"), index=True)

    enabled: Mapped[bool | None] = mapped_column(Boolean, default=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[HttpUrlType | None] = mapped_column(HttpUrlType, nullable=False)
    method: Mapped[Enum[Method]] = mapped_column(Enum(Method), default=Method.POST)

    # New Fields
    webhook_type: Mapped[str | None] = mapped_column(
        Enum(EventDocumentType), default="generic"
    )  # Future use for different types of webhooks
    scheduled_time: Mapped[time | None] = mapped_column(Time, default=lambda: datetime.now(timezone.utc).time())

    @auto_init()
    def __init__(self, **_) -> None: ...
