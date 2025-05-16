from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.httpurl import HttpUrlType
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from ..groups import Groups


class GroupEventNotifierOptionsModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "group_events_notifier_options"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    event_notifier_id: Mapped[GUID] = mapped_column(GUID, ForeignKey("group_events_notifiers.id"), nullable=False)
    user_signup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class GroupEventNotifierModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "group_events_notifiers"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    name: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    apprise_url: Mapped[str] = mapped_column(String, nullable=False)

    group: Mapped[Optional["Groups"]] = orm.relationship(
        "Groups", back_populates="group_event_notifiers", single_parent=True
    )
    group_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("groups.id"), index=True)

    options: Mapped[GroupEventNotifierOptionsModel] = orm.relationship(
        GroupEventNotifierOptionsModel, uselist=False, cascade="all, delete-orphan"
    )

    @auto_init()
    def __init__(self, **_) -> None:
        pass
