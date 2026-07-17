"""SQLAlchemy model for per-workspace AI workflow policy settings."""

from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, Session, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .groups import Groups


class WorkspaceAISettingsModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "workspace_ai_settings"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: Mapped[GUID] = mapped_column(
        GUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="ai_settings")

    enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    # "platform" | "workspace" | "disabled"
    credential_mode: Mapped[str] = mapped_column(sa.String, default="platform", nullable=False)
    # "openai" | "anthropic" | ...
    provider: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    model: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    # slug of a WorkspaceSecret
    secret_ref: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    # "suggest-only" | "allow-draft-update" | "allow-automatic-update"
    approval_mode: Mapped[str] = mapped_column(sa.String, default="suggest-only", nullable=False)

    # {editor, forms, actions, mcp, scheduledJobs} — which subsystems may call AI
    invocation_sources: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    # per-operation {model, approval_mode, ...}
    operation_overrides: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    # {max_tokens_per_request, max_requests_per_day, ...}
    budget_config: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    # {log_inputs, log_outputs, redact_patterns, retention_days}
    logging_config: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    # {enabled, block_on_flag}
    moderation_config: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        pass
