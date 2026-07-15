"""
Publishing task handlers for content management.

These handlers manage scheduled publishing, unpublishing, and site rebuild triggers.
"""

from datetime import UTC, datetime
from uuid import UUID

from marvin.core.root_logger import get_logger
from marvin.db.db_setup import session_context
from marvin.db.models.platform.entries import Entries
from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel
from marvin.repos.repository_factory import AllRepositories
from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import EventTypes

from . import ScheduledTaskHandler, TaskHandlerRegistry

logger = get_logger(__name__)


class PublishScheduledEntriesHandler(ScheduledTaskHandler):
    """
    Publish entries with publish_at <= now.

    Configuration (task_config):
    - workspace_id: str (required) - Workspace to scan for scheduled entries
    - dry_run: bool (default: False) - If true, log what would be published
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        raw_workspace_id = config.get("workspace_id") or task.group_id
        dry_run = config.get("dry_run", False)

        if not raw_workspace_id:
            raise ValueError("workspace_id is required in task_config or task.group_id")

        workspace_id = UUID(str(raw_workspace_id))

        with session_context() as session:
            now = datetime.now(UTC)
            logger.info(
                "Scanning for scheduled entries in workspace %s (now=%s, dry_run=%s)",
                workspace_id,
                now,
                dry_run,
            )

            scheduled_entries = (
                session.query(Entries)
                .filter(
                    Entries.group_id == workspace_id,
                    Entries.publish_at <= now,
                    Entries.status != "published",
                )
                .all()
            )

            logger.info("Found %d entries to publish", len(scheduled_entries))

            for entry in scheduled_entries:
                if not dry_run:
                    entry.status = "published"
                    entry.published_at = now
                    session.commit()
                    logger.info("Published entry '%s' (id=%s)", entry.title, entry.id)

                    event_bus.dispatch(
                        integration_id="scheduled_tasks",
                        group_id=workspace_id,
                        event_type=EventTypes.entry_published,
                        document_data=None,
                        message=f"Entry '{entry.title}' published via scheduled task",
                    )
                else:
                    logger.info(
                        "Would publish: %s (id=%s, publish_at=%s)",
                        entry.title,
                        entry.id,
                        entry.publish_at,
                    )


class UnpublishExpiredEntriesHandler(ScheduledTaskHandler):
    """
    Unpublish entries with expire_at <= now.

    Configuration (task_config):
    - workspace_id: str (required) - Workspace to scan for expired entries
    - dry_run: bool (default: False) - If true, log what would be unpublished
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        raw_workspace_id = config.get("workspace_id") or task.group_id
        dry_run = config.get("dry_run", False)

        if not raw_workspace_id:
            raise ValueError("workspace_id is required in task_config or task.group_id")

        workspace_id = UUID(str(raw_workspace_id))

        with session_context() as session:
            now = datetime.now(UTC)
            logger.info(
                "Scanning for expired entries in workspace %s (now=%s, dry_run=%s)",
                workspace_id,
                now,
                dry_run,
            )

            expired_entries = (
                session.query(Entries)
                .filter(
                    Entries.group_id == workspace_id,
                    Entries.expire_at <= now,
                    Entries.status == "published",
                )
                .all()
            )

            logger.info("Found %d expired entries", len(expired_entries))

            for entry in expired_entries:
                if not dry_run:
                    entry.status = "archived"
                    session.commit()
                    logger.info("Unpublished expired entry '%s' (id=%s)", entry.title, entry.id)

                    event_bus.dispatch(
                        integration_id="scheduled_tasks",
                        group_id=workspace_id,
                        event_type=EventTypes.entry_unpublished,
                        document_data=None,
                        message=f"Entry '{entry.title}' unpublished (expired)",
                    )
                else:
                    logger.info(
                        "Would unpublish: %s (id=%s, expire_at=%s)",
                        entry.title,
                        entry.id,
                        entry.expire_at,
                    )


class RequestSiteRebuildHandler(ScheduledTaskHandler):
    """
    Trigger a static site rebuild via webhook.

    Configuration (task_config):
    - workspace_id: str (required) - Workspace context for the rebuild
    - reason: str (default: "scheduled") - Reason for the rebuild
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        raw_workspace_id = config.get("workspace_id") or task.group_id
        reason = config.get("reason", "scheduled")

        if not raw_workspace_id:
            raise ValueError("workspace_id is required in task_config or task.group_id")

        workspace_id = UUID(str(raw_workspace_id))

        event_bus.dispatch(
            integration_id="scheduled_tasks",
            group_id=workspace_id,
            event_type=EventTypes.webhook_triggered,
            document_data=None,
            message=f"Site rebuild requested: {reason}",
        )

        logger.info("Site rebuild requested for workspace %s (reason: %s)", workspace_id, reason)


# Register handlers
TaskHandlerRegistry.register("publish_scheduled_entries", PublishScheduledEntriesHandler)
TaskHandlerRegistry.register("unpublish_expired_entries", UnpublishExpiredEntriesHandler)
TaskHandlerRegistry.register("request_site_rebuild", RequestSiteRebuildHandler)
