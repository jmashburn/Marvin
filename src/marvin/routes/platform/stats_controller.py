"""Platform stats endpoint — returns workspace-scoped resource counts."""

import datetime

from fastapi import APIRouter
from pydantic import UUID4

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


@controller(router)
class StatsController(BaseUserController):
    """Returns resource counts for the current workspace."""

    @router.get("", response_model=WorkspaceStats, summary="Get Workspace Statistics")
    def get_stats(self) -> WorkspaceStats:
        workspace_id: UUID4 = self.group_id

        members = self.repos.workspace_members.get_members_by_workspace(workspace_id)

        return WorkspaceStats(
            entries=self.repos.entries.count_all(),
            assets=self.repos.assets.count_all(),
            collections=self.repos.collections.count_all(),
            webhooks=self.repos.webhooks.count_all(),
            scheduled_tasks=self.repos.scheduled_tasks.count_all(),
            secrets=self.repos.workspace_secrets().count_all(),
            variables=self.repos.workspace_variables().count_all(),
            members=len(members),
        )
