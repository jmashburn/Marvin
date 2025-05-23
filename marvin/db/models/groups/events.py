from typing import TYPE_CHECKING, Optional, cast

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, orm, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from pydantic import ConfigDict


from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.httpurl import HttpUrlType
from .._model_utils.guid import GUID
from slugify import slugify

if TYPE_CHECKING:
    from ..groups import Groups


class GroupEventNotifierOptionsModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "group_events_notifier_options"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    namespace: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    group_event_notifiers: Mapped[list["GroupEventNotifierModel"]] = orm.relationship(
        "GroupEventNotifierModel", back_populates="options"
    )
    group_event_notifiers_id: Mapped[GUID | None] = mapped_column(
        GUID, ForeignKey("group_events_notifiers.id"), index=True
    )

    @hybrid_property
    def option(self) -> str:
        return self.namespace + "." + self.slug

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
    options: Mapped[list[GroupEventNotifierOptionsModel]] = orm.relationship(
        "GroupEventNotifierOptionsModel", back_populates="group_event_notifiers"
    )

    model_config = ConfigDict(
        exclude={
            "options",
        }
    )

    @auto_init()
    def __init__(self, session: Session, options: list | None = None, **kwargs) -> None:
        from marvin.db.models.events import EventNotifierOptionsModel

        enabled_options = (
            session.execute(select(EventNotifierOptionsModel).filter(EventNotifierOptionsModel.enabled == True))
            .scalars()
            .all()
        )
        if enabled_options is not None:
            self.options = [
                GroupEventNotifierOptionsModel(
                    session=session,
                    namespace=enabled_option.namespace,
                    slug=enabled_option.slug,
                    enabled=enabled_option.enabled,
                )
                for enabled_option in enabled_options
            ]

        if options is not None:
            for option in options:
                namespace, slug = option.split(".")
                new_option = (
                    session.execute(
                        select(EventNotifierOptionsModel).filter(
                            EventNotifierOptionsModel.slug == slug, EventNotifierOptionsModel.namespace == namespace
                        )
                    )
                    .scalars()
                    .one()
                )
                if new_option is None:
                    raise ValueError(f"Option {option} does not exist; cannont create event notifications")

                self.options.append(
                    GroupEventNotifierOptionsModel(
                        session=session, namespace=new_option.namespace, slug=new_option.slug, enabled=True
                    )
                )
