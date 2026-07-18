from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.datetime import DateTime
from .._model_utils.guid import GUID


class NotificationExecutionLogModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "notification_execution_logs"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    notifier_id: Mapped[GUID] = mapped_column(
        GUID,
        ForeignKey("group_events_notifiers.id", ondelete="CASCADE"),
        index=True,
    )

    group_id: Mapped[GUID] = mapped_column(
        GUID,
        ForeignKey("groups.id", ondelete="CASCADE"),
        index=True,
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )

    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    request_payload: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        pass
