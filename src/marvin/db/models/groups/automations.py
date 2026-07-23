"""SQLAlchemy model for per-workspace user-configured automations (Flavor B).

An automation is a data-defined reaction: a trigger event, a conditions matcher, and an ordered
`actions` pipeline — authored by a workspace admin rather than hardcoded in a listener class
(contrast the Flavor A developer-defined reactions in `_get_listeners`). One generic listener
(`AutomationReactionListener`) loads and runs these rows.
"""

from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, Session, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .groups import Groups


class WorkspaceAutomationModel(SqlAlchemyBase, BaseMixins):
    """A user-configured automation: `event → conditions → actions`.

    `definition` holds the whole rule as JSON:
        {
          "trigger":    {"event": "entry_published"},
          "conditions": [{"field": "entry.entry_type", "op": "eq", "value": "recipe"}],
          "actions":    [{"kind": "operation", "op": "generate-summary",
                          "input": {}, "write_back": true}]
        }

    Deny-by-default: an automation does nothing unless `enabled` is true AND its actions pass the
    `invocation_sources` gate for the `"automation"` source. Managed by ADMIN/OWNER.
    """

    __tablename__ = "workspace_automations"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="automations")

    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String, nullable=False)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    # The full rule: {trigger, conditions, actions}. Validated by the engine, not the DB.
    definition: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    created_by: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (sa.UniqueConstraint("group_id", "slug", name="uq_automations_group_slug"),)

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        pass
