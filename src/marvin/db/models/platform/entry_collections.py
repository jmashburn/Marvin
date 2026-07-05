"""Entry-Collections junction table."""

from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import SqlAlchemyBase
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .collections import Collections
    from .entries import Entries


class EntryCollections(SqlAlchemyBase):
    """Junction table for many-to-many relationship between entries and collections."""

    __tablename__ = "entry_collections"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    entry_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    # Relationships for easier access
    collection: Mapped["Collections"] = orm.relationship(
        "Collections",
        overlaps="collections,entries",
    )
    entry: Mapped["Entries"] = orm.relationship(
        "Entries",
        overlaps="collections,entries,entry_collections",
    )

    __table_args__ = (sa.UniqueConstraint("entry_id", "collection_id"),)
