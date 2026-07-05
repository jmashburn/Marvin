"""Entry model."""

from typing import TYPE_CHECKING
from datetime import datetime

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, Session, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .entry_types import EntryTypes


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
    published_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)

    entry_type: Mapped["EntryTypes"] = orm.relationship("EntryTypes", back_populates="entries")

    __table_args__ = (
        sa.UniqueConstraint("group_id", "slug"),
        sa.Index("ix_entries_group_status", "group_id", "status"),
    )

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """Initialize via Marvin's auto-init model helper."""
        pass
