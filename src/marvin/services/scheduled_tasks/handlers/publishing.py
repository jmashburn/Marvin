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
    Publish entries with publish_at <= now, scoped to the task's workspace.

    Configuration (task_config):
    - dry_run: bool (default: False) - If true, log what would be published
    """

    name = "Publish Scheduled Entries"
    description = "Publish entries whose publish_at time has arrived"

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> str | None:
        config = task.task_config
        dry_run = config.get("dry_run", False)

        if not task.group_id:
            raise ValueError("Task has no workspace scope — cannot publish entries")

        workspace_id = UUID(str(task.group_id))

        with session_context() as session:
            now = datetime.now(UTC)

            scheduled_entries = (
                session.query(Entries)
                .filter(
                    Entries.group_id == workspace_id,
                    Entries.publish_at <= now,
                    Entries.status != "published",
                )
                .all()
            )

            count = len(scheduled_entries)
            logger.info(
                "Found %d entries to publish in workspace %s (dry_run=%s)",
                count, workspace_id, dry_run,
            )

            published_titles = []
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
                        entry.title, entry.id, entry.publish_at,
                    )
                published_titles.append(entry.title)

        if count == 0:
            summary = "No entries due for publishing"
        else:
            label = "would publish" if dry_run else "published"
            names = ", ".join(f"'{t}'" for t in published_titles[:5])
            suffix = f" and {count - 5} more" if count > 5 else ""
            summary = f"{count} entr{'y' if count == 1 else 'ies'} {label}: {names}{suffix}"
            if dry_run:
                summary += " (dry run)"

        logger.info("Publish scheduled entries: %s", summary)
        return summary


class UnpublishExpiredEntriesHandler(ScheduledTaskHandler):
    """
    Unpublish entries with expire_at <= now, scoped to the task's workspace.

    Configuration (task_config):
    - dry_run: bool (default: False) - If true, log what would be unpublished
    """

    name = "Unpublish Expired Entries"
    description = "Archive entries whose expire_at time has passed"

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> str | None:
        config = task.task_config
        dry_run = config.get("dry_run", False)

        if not task.group_id:
            raise ValueError("Task has no workspace scope — cannot unpublish entries")

        workspace_id = UUID(str(task.group_id))

        with session_context() as session:
            now = datetime.now(UTC)

            expired_entries = (
                session.query(Entries)
                .filter(
                    Entries.group_id == workspace_id,
                    Entries.expire_at <= now,
                    Entries.status == "published",
                )
                .all()
            )

            count = len(expired_entries)
            logger.info(
                "Found %d expired entries in workspace %s (dry_run=%s)",
                count, workspace_id, dry_run,
            )

            expired_titles = []
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
                        entry.title, entry.id, entry.expire_at,
                    )
                expired_titles.append(entry.title)

        if count == 0:
            summary = "No entries found past their expiry date"
        else:
            label = "would unpublish" if dry_run else "archived"
            names = ", ".join(f"'{t}'" for t in expired_titles[:5])
            suffix = f" and {count - 5} more" if count > 5 else ""
            summary = f"{count} entr{'y' if count == 1 else 'ies'} {label}: {names}{suffix}"
            if dry_run:
                summary += " (dry run)"

        logger.info("Unpublish expired entries: %s", summary)
        return summary


class RequestSiteRebuildHandler(ScheduledTaskHandler):
    """
    Trigger a static site rebuild via webhook, scoped to the task's workspace.

    Configuration (task_config):
    - reason: str (default: "scheduled") - Reason for the rebuild
    """

    name = "Request Site Rebuild"
    description = "Dispatch a webhook_triggered event to kick off a static site rebuild"

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> str | None:
        config = task.task_config
        reason = config.get("reason", "scheduled")

        if not task.group_id:
            raise ValueError("Task has no workspace scope — cannot request site rebuild")

        workspace_id = UUID(str(task.group_id))

        event_bus.dispatch(
            integration_id="scheduled_tasks",
            group_id=workspace_id,
            event_type=EventTypes.webhook_triggered,
            document_data=None,
            message=f"Site rebuild requested: {reason}",
        )

        summary = f"Site rebuild event dispatched (workspace: {workspace_id}, reason: {reason})"
        logger.info(summary)
        return summary


# Register handlers
TaskHandlerRegistry.register("publish_scheduled_entries", PublishScheduledEntriesHandler)
TaskHandlerRegistry.register("unpublish_expired_entries", UnpublishExpiredEntriesHandler)
TaskHandlerRegistry.register("request_site_rebuild", RequestSiteRebuildHandler)
