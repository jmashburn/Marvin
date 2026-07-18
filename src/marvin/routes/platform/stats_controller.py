"""Platform stats endpoint — returns workspace-scoped resource counts."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import UUID4
from sqlalchemy import func, select

from marvin.db.models.groups import GroupWebhooksModel
from marvin.db.models.groups.ai_embeddings import AIEmbeddingModel
from marvin.db.models.groups.ai_executions import AIExecutionModel
from marvin.db.models.groups.secrets import WorkspaceSecret
from marvin.db.models.groups.variables import WorkspaceVariable
from marvin.db.models.platform import Assets, Collections, Entries
from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel
from marvin.routes._base import BaseUserController, controller
from marvin.schemas._marvin import _MarvinModel

router = APIRouter(prefix="/stats")


class WorkspaceStats(_MarvinModel):
    entries: int = 0
    assets: int = 0
    collections: int = 0
    webhooks: int = 0
    scheduled_tasks: int = 0
    secrets: int = 0
    variables: int = 0
    members: int = 0
    ai_executions: int = 0
    ai_embeddings: int = 0
    ai_tokens: int = 0
    ai_cost_usd: float = 0.0


def _count(session, model, group_id: UUID4) -> int:
    """Return a group-scoped row count, defaulting to 0 on any error."""
    try:
        return (
            session.execute(
                select(func.count(model.id)).where(model.group_id == group_id)
            ).scalar()
            or 0
        )
    except Exception:
        return 0


def _sum(session, model, column, group_id: UUID4, since: datetime | None = None):
    """Return a group-scoped SUM of `column`, optionally since `since`, defaulting to 0 on error."""
    try:
        stmt = select(func.coalesce(func.sum(column), 0)).where(model.group_id == group_id)
        if since is not None:
            stmt = stmt.where(model.created_at >= since)
        return session.execute(stmt).scalar() or 0
    except Exception:
        return 0


@controller(router)
class StatsController(BaseUserController):
    """Returns resource counts for the current workspace."""

    @router.get("", response_model=WorkspaceStats, summary="Get Workspace Statistics")
    def get_stats(self) -> WorkspaceStats:
        workspace_id: UUID4 = self.group_id
        session = self.repos.session
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        try:
            members = self.repos.workspace_members.get_members_by_workspace(workspace_id)
            members_count = len(members)
        except Exception:
            members_count = 0

        return WorkspaceStats(
            entries=_count(session, Entries, workspace_id),
            assets=_count(session, Assets, workspace_id),
            collections=_count(session, Collections, workspace_id),
            webhooks=_count(session, GroupWebhooksModel, workspace_id),
            scheduled_tasks=_count(session, ScheduledTaskModel, workspace_id),
            secrets=_count(session, WorkspaceSecret, workspace_id),
            variables=_count(session, WorkspaceVariable, workspace_id),
            members=members_count,
            ai_executions=_count(session, AIExecutionModel, workspace_id),
            ai_embeddings=_count(session, AIEmbeddingModel, workspace_id),
            # Tokens + cost are month-to-date usage flows, aligned with the monthly budget limit.
            ai_tokens=int(_sum(session, AIExecutionModel, AIExecutionModel.total_tokens, workspace_id, since=month_start)),
            ai_cost_usd=float(_sum(session, AIExecutionModel, AIExecutionModel.estimated_cost_usd, workspace_id, since=month_start)),
        )
