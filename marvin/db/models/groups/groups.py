from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from pydantic import ConfigDict
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID
from .preferences import GroupPreferencesModel

if TYPE_CHECKING:
    from ..users import Users
    from .events import GroupEventNotifierModel
    from .invite_tokens import GroupInviteToken
    from .reports import ReportModel
    from .webhooks import GroupWebhooksModel


class Groups(SqlAlchemyBase, BaseMixins):
    __tablename__ = "groups"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    name: Mapped[str] = mapped_column(sa.String, index=True, nullable=False, unique=True)
    slug: Mapped[str | None] = mapped_column(sa.String, index=True, unique=True)
    users: Mapped[list["Users"]] = orm.relationship("Users", back_populates="group")

    preferences: Mapped[GroupPreferencesModel] = orm.relationship(
        GroupPreferencesModel,
        back_populates="group",
        uselist=False,
        single_parent=True,
        cascade="all, delete-orphan",
    )

    # CRUD From Others
    common_args = {
        "back_populates": "group",
        "cascade": "all, delete-orphan",
        "single_parent": True,
    }

    invite_tokens: Mapped[list["GroupInviteToken"]] = orm.relationship("GroupInviteToken", **common_args)
    webhooks: Mapped[list["GroupWebhooksModel"]] = orm.relationship("GroupWebhooksModel", **common_args)
    group_reports: Mapped[list["ReportModel"]] = orm.relationship("ReportModel", **common_args)
    group_event_notifiers: Mapped[list["GroupEventNotifierModel"]] = orm.relationship(
        "GroupEventNotifierModel", **common_args
    )

    model_config = ConfigDict(
        exclude={
            "users",
            "webhooks",
            "preferences",
            "invite_tokens",
        }
    )

    @auto_init()
    def __init__(self, **_) -> None:
        pass
