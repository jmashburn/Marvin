"""Collections model - curated groupings of entries."""

from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, Session, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .entries import Entries


class Collections(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a collection.

    Collections are curated groupings of entries. They can be manual or smart.
    """

    __tablename__ = "collections"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0, server_default="0")
    icon: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    color: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    is_smart: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    smart_rules: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

    # Relationships
    entries: Mapped[list["Entries"]] = orm.relationship(
        "Entries",
        secondary="entry_collections",
        back_populates="collections",
        doc="Entries in this collection",
    )

    __table_args__ = (sa.UniqueConstraint("group_id", "slug"),)

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """Initialize via Marvin's auto-init model helper."""
        pass
