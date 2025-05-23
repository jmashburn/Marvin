from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, orm
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


class EventNotifierOptionsModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "events_notifier_options"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    namespace: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @hybrid_property
    def option(self) -> str:
        return self.namespace + "." + self.slug

    @auto_init()
    def __init__(self, session: orm.Session, name: str, **_) -> None:
        self.slug = slugify(name)
