from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .groups import Groups


class GroupPreferencesModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "group_preferences"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    group_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("groups.id"), nullable=False, index=True)
    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="preferences")

    private_group: Mapped[bool | None] = mapped_column(sa.Boolean, default=True)
    first_day_of_week: Mapped[int | None] = mapped_column(sa.Integer, default=0)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
