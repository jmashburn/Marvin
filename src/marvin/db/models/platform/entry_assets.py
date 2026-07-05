"""Entry-Assets junction table."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .. import SqlAlchemyBase
from .._model_utils.guid import GUID


class EntryAssets(SqlAlchemyBase):
    """Junction table for many-to-many relationship between entries and assets."""

    __tablename__ = "entry_assets"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    entry_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    role: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    usage: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    focal_point: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    caption: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", sa.JSON, nullable=True)

    __table_args__ = (sa.UniqueConstraint("entry_id", "asset_id"),)
