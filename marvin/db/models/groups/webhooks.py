from datetime import datetime, time, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Time, orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .groups import Groups


class GroupWebhooksModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "webhook_urls"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="webhooks", single_parent=True)
    group_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("groups.id"), index=True)

    enabled: Mapped[bool | None] = mapped_column(Boolean, default=False)
    name: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)

    # New Fields
    webhook_type: Mapped[str | None] = mapped_column(String, default="")  # Future use for different types of webhooks
    scheduled_time: Mapped[time | None] = mapped_column(Time, default=lambda: datetime.now(timezone.utc).time())

    @auto_init()
    def __init__(self, **_) -> None: ...
