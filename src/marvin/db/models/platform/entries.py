"""Entry model."""

from typing import TYPE_CHECKING
from datetime import datetime

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, Session, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.datetime import NaiveDateTime
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from ..users import Users
    from .assets import Assets
    from .collections import Collections
    from .entry_assets import EntryAssets
    from .entry_collections import EntryCollections
    from .entry_resources import EntryResources
    from .entry_types import EntryTypes
    from .resources import Resources


class Entries(SqlAlchemyBase, BaseMixins):
    """Workspace-scoped publishable content entry."""

    __tablename__ = "entries"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("entry_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(sa.String, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String, nullable=False)
    summary: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    description: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    content_markdown: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(sa.String, nullable=False, default="inbox", server_default="inbox")
    published_at: Mapped[datetime | None] = mapped_column(NaiveDateTime, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata_json", sa.JSON, nullable=True)
    created_by: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    entry_type: Mapped["EntryTypes"] = orm.relationship("EntryTypes", back_populates="entries")
    author: Mapped["Users"] = orm.relationship("Users", foreign_keys=[created_by])
    collections: Mapped[list["Collections"]] = orm.relationship(
        "Collections",
        secondary="entry_collections",
        back_populates="entries",
        doc="Collections this entry belongs to",
    )
    entry_collections: Mapped[list["EntryCollections"]] = orm.relationship(
        "EntryCollections",
        foreign_keys="EntryCollections.entry_id",
        overlaps="collections,entries",
        cascade="all, delete-orphan",
        doc="Direct access to entry-collection associations",
    )

    resources: Mapped[list["Resources"]] = orm.relationship(
        "Resources",
        secondary="entry_resources",
        back_populates="entries",
        doc="Resources referenced by this entry",
    )

    entry_resources: Mapped[list["EntryResources"]] = orm.relationship(
        "EntryResources",
        foreign_keys="EntryResources.entry_id",
        overlaps="entries,resources",
        cascade="all, delete-orphan",
        doc="Direct access to entry-resource associations with placement info",
    )

    assets: Mapped[list["Assets"]] = orm.relationship(
        "Assets",
        secondary="entry_assets",
        back_populates="entries",
        doc="Assets included in this entry",
    )

    entry_assets: Mapped[list["EntryAssets"]] = orm.relationship(
        "EntryAssets",
        foreign_keys="EntryAssets.entry_id",
        overlaps="assets,entries",
        cascade="all, delete-orphan",
        doc="Direct access to entry-asset associations with placement info",
    )

    __table_args__ = (
        sa.UniqueConstraint("group_id", "slug"),
        sa.Index("ix_entries_group_status", "group_id", "status"),
    )

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """Initialize via Marvin's auto-init model helper."""
        pass
