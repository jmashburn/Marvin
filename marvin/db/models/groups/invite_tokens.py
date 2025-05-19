from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.guid import GUID
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from .groups import Groups


class GroupInviteToken(SqlAlchemyBase, BaseMixins):
    __tablename__ = "invite_tokens"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    token: Mapped[str] = mapped_column(String, index=True, nullable=False, unique=True)
    uses_left: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    group_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("groups.id"), index=True)
    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="invite_tokens")

    @auto_init()
    def __init__(self, **_):
        pass
