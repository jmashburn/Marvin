"""Entry-Assets junction table."""

from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import SqlAlchemyBase
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .assets import Assets
    from .entries import Entries


class EntryAssets(SqlAlchemyBase):
    """Junction table for many-to-many relationship between entries and assets."""

    __tablename__ = "entry_assets"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    entry_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    role: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    focal_point: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    caption: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", sa.JSON, nullable=True)

    # Relationships
    entry: Mapped["Entries"] = orm.relationship(
        "Entries",
        foreign_keys=[entry_id],
        overlaps="assets,entries,entry_assets",
    )
    asset: Mapped["Assets"] = orm.relationship(
        "Assets",
        foreign_keys=[asset_id],
        back_populates="entry_assets",
        overlaps="assets,entries",
    )

    __table_args__ = (
        sa.UniqueConstraint("entry_id", "asset_id"),
        sa.Index("ix_entry_assets_entry_id_position", "entry_id", "position"),
    )
