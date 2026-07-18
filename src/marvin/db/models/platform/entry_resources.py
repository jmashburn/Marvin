"""Entry-Resources junction table."""

from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import SqlAlchemyBase
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .entries import Entries
    from .resources import Resources


class EntryResources(SqlAlchemyBase):
    """Junction table for many-to-many relationship between entries and resources."""

    __tablename__ = "entry_resources"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    entry_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

    # Relationships
    entry: Mapped["Entries"] = orm.relationship(
        "Entries",
        foreign_keys=[entry_id],
        overlaps="entries,resources,entry_resources",
    )
    resource: Mapped["Resources"] = orm.relationship(
        "Resources",
        foreign_keys=[resource_id],
        back_populates="entry_resources",
        overlaps="entries,resources,entry_resources",
    )

    __table_args__ = (
        sa.UniqueConstraint("entry_id", "resource_id"),
        sa.Index("ix_entry_resources_entry_id_position", "entry_id", "position"),
    )
