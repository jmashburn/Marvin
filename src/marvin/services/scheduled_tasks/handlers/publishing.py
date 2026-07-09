"""
Publishing task handlers for content management.

These handlers manage scheduled publishing, unpublishing, and site rebuild triggers.
"""

import logging
from datetime import datetime

from marvin.db.db_setup import session_context
from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel
from marvin.repos.repository_factory import AllRepositories
from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import EventTypes

from . import ScheduledTaskHandler, TaskHandlerRegistry

logger = logging.getLogger(__name__)


class PublishScheduledEntriesHandler(ScheduledTaskHandler):
    """
    Publish entries with publish_at <= now.

    Configuration (task_config):
    - workspace_id: str (required) - Workspace to scan for scheduled entries
    - dry_run: bool (default: False) - If true, log what would be published
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        workspace_id = config.get("workspace_id") or task.group_id
        dry_run = config.get("dry_run", False)

        if not workspace_id:
            raise ValueError("workspace_id is required in task_config or task.group_id")

        with session_context() as session:
            repos = AllRepositories(session, group_id=workspace_id)

            # Find entries with publish_at <= now and status != 'published'
            # This is a simplified example - actual implementation would query properly
            now = datetime.utcnow()
            logger.info(
                "Scanning for scheduled entries in workspace %s (now=%s, dry_run=%s)",
                workspace_id,
                now,
                dry_run,
            )

            # TODO: Implement actual query for entries with publish_at <= now
            # For each entry found:
            # 1. Update status to 'published'
            # 2. Emit entry.published event
            # Example:
            # for entry in scheduled_entries:
            #     if not dry_run:
            #         repos.entries.update(entry.id, {"status": "published"})
            #         event_bus.dispatch(
            #             integration_id="scheduled_tasks",
            #             group_id=workspace_id,
            #             event_type=EventTypes.entry_published,
            #             document_data=...,
            #             message=f"Entry '{entry.title}' published via scheduled task",
            #         )
            #     else:
            #         logger.info("Would publish: %s", entry.title)


class UnpublishExpiredEntriesHandler(ScheduledTaskHandler):
    """
    Unpublish entries with expires_at <= now.

    Configuration (task_config):
    - workspace_id: str (required) - Workspace to scan for expired entries
    - dry_run: bool (default: False) - If true, log what would be unpublished
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        workspace_id = config.get("workspace_id") or task.group_id
        dry_run = config.get("dry_run", False)

        if not workspace_id:
            raise ValueError("workspace_id is required in task_config or task.group_id")

        with session_context() as session:
            repos = AllRepositories(session, group_id=workspace_id)

            now = datetime.utcnow()
            logger.info(
                "Scanning for expired entries in workspace %s (now=%s, dry_run=%s)",
                workspace_id,
                now,
                dry_run,
            )

            # TODO: Implement actual query for entries with expires_at <= now
            # For each entry found:
            # 1. Update status to 'draft' or 'archived'
            # 2. Emit entry.unpublished event


class RequestSiteRebuildHandler(ScheduledTaskHandler):
    """
    Trigger a static site rebuild via webhook.

    Configuration (task_config):
    - workspace_id: str (required) - Workspace context for the rebuild
    - reason: str (default: "scheduled") - Reason for the rebuild
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        workspace_id = config.get("workspace_id") or task.group_id
        reason = config.get("reason", "scheduled")

        if not workspace_id:
            raise ValueError("workspace_id is required in task_config or task.group_id")

        # Emit a rebuild event that webhooks can listen for
        event_bus.dispatch(
            integration_id="scheduled_tasks",
            group_id=workspace_id,
            event_type="site.rebuild_requested",  # Custom event type
            document_data={"reason": reason, "triggered_by": "scheduled_task", "task_id": str(task.id)},
            message=f"Site rebuild requested: {reason}",
        )

        logger.info("Site rebuild requested for workspace %s (reason: %s)", workspace_id, reason)


# Register handlers
TaskHandlerRegistry.register("publish_scheduled_entries", PublishScheduledEntriesHandler)
TaskHandlerRegistry.register("unpublish_expired_entries", UnpublishExpiredEntriesHandler)
TaskHandlerRegistry.register("request_site_rebuild", RequestSiteRebuildHandler)
