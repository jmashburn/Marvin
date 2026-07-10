"""Form rate limiting model."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, Session, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.datetime import NaiveDateTime
from .._model_utils.guid import GUID


class FormRateLimits(SqlAlchemyBase, BaseMixins):
    """Rate limiting tracker for form submissions.

    Tracks submission counts per identifier (IP or API client) within
    sliding time windows to enforce rate limits per form.
    """

    __tablename__ = "form_rate_limits"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    form_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("forms.id", ondelete="CASCADE"), nullable=False, index=True)

    identifier: Mapped[str] = mapped_column(sa.String, nullable=False)
    """IP address or API client ID."""

    window_start: Mapped[datetime] = mapped_column(NaiveDateTime, nullable=False, index=True)
    """Start of rate limit window."""

    submission_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1, server_default="1")
    """Number of submissions in this window."""

    __table_args__ = (
        sa.UniqueConstraint("form_id", "identifier", "window_start", name="uq_rate_limit_form_identifier_window"),
        sa.Index("ix_rate_limits_form_identifier", "form_id", "identifier"),
    )

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """Initialize via Marvin's auto-init model helper."""
        pass
