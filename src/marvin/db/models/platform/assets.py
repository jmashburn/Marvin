"""Assets model - uploaded files."""

from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .entries import Entries


class Assets(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing an asset.

    Assets are uploaded files like images, PDFs, audio, video, etc.
    """

    __tablename__ = "assets"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(sa.String, nullable=False)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    file_path: Mapped[str] = mapped_column(sa.String, nullable=False)
    file_size: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    width: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    description: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", sa.JSON, nullable=True)
    uploaded_by: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    entries: Mapped[list["Entries"]] = orm.relationship(
        "Entries",
        secondary="entry_assets",
        back_populates="assets",
        doc="Entries that include this asset",
    )

    __table_args__ = (sa.UniqueConstraint("group_id", "slug"),)
