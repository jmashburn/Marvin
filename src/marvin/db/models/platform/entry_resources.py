"""Entry-Resources junction table."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .. import SqlAlchemyBase
from .._model_utils.guid import GUID


class EntryResources(SqlAlchemyBase):
    """Junction table for many-to-many relationship between entries and resources."""

    __tablename__ = "entry_resources"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    entry_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    quantity: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    unit: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    __table_args__ = (sa.UniqueConstraint("entry_id", "resource_id"),)
