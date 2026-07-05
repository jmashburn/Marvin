"""Site Clients model - read-only API identities for external sites."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.guid import GUID


class SiteClients(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a site client.

    Site clients are read-only API identities for external sites consuming published content.
    """

    __tablename__ = "site_clients"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String, nullable=False)
    token_hash: Mapped[str] = mapped_column(sa.String, nullable=False, unique=True, index=True)
    permissions: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    last_used_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime, nullable=True)
    created_by: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    revoked_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime, nullable=True)

    __table_args__ = (sa.UniqueConstraint("group_id", "slug"),)
