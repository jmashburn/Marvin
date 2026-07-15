"""
Maintenance task handlers for cleanup and housekeeping.

These handlers perform routine maintenance operations like cleaning up temp files,
pruning old data, and verifying system integrity.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from marvin.core.root_logger import get_logger
from marvin.db.db_setup import session_context
from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel
from marvin.repos.repository_factory import AllRepositories
from marvin.services.event_bus_service.event_bus_service import EventBusService

from . import ScheduledTaskHandler, TaskHandlerRegistry

logger = get_logger(__name__)


class CleanupTempFilesHandler(ScheduledTaskHandler):
    """
    Remove old files from temporary upload storage.

    Configuration (task_config):
    - age_hours: int (default: 24) - Files older than this are deleted
    - dry_run: bool (default: False) - If true, log what would be deleted
    """

    name = "Cleanup Temporary Files"
    description = "Remove old files from temporary upload storage"
    config_schema = {
        "type": "object",
        "properties": {
            "age_hours": {
                "type": "integer",
                "default": 24,
                "description": "Files older than this many hours will be deleted",
            },
            "dry_run": {
                "type": "boolean",
                "default": False,
                "description": "If true, log what would be deleted without actually deleting",
            },
        },
    }

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        age_hours = config.get("age_hours", 24)
        dry_run = config.get("dry_run", False)

        from marvin.core.config import get_app_dirs
        temp_dir = get_app_dirs().TEMP_DIR

        if not temp_dir.exists():
            logger.info("Temp directory does not exist: %s", temp_dir)
            return

        cutoff = datetime.now(UTC) - timedelta(hours=age_hours)
        deleted_count = 0
        deleted_bytes = 0

        for file_path in temp_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Check file modification time
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < cutoff:
                file_size = file_path.stat().st_size
                if dry_run:
                    logger.info("Would delete: %s (%d bytes)", file_path, file_size)
                else:
                    file_path.unlink()
                    logger.debug("Deleted: %s (%d bytes)", file_path, file_size)
                deleted_count += 1
                deleted_bytes += file_size

        logger.info(
            "Temp file cleanup: %d files, %d bytes %s",
            deleted_count,
            deleted_bytes,
            "(dry run)" if dry_run else "deleted",
        )


class PruneExpiredSessionsHandler(ScheduledTaskHandler):
    """
    Remove expired user sessions from the database.

    Configuration (task_config):
    - age_days: int (default: 7) - Sessions older than this are deleted
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        # Note: This is a placeholder - Marvin uses JWT tokens, not database sessions
        # If session storage is added later, implement cleanup here
        logger.info("Session cleanup handler called (no-op - Marvin uses JWT)")


class PruneExpiredInvitationsHandler(ScheduledTaskHandler):
    """
    Remove expired workspace invitations.

    Configuration (task_config):
    - age_days: int (default: 30) - Invitations older than this are deleted
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        age_days = config.get("age_days", 30)

        with session_context() as session:
            repos = AllRepositories(session, group_id=None)  # System-wide access

            # Get all invitations (workspace-scoped repos need group context)
            # This is a simplified example - actual implementation would need
            # to iterate over workspaces or use a direct query
            logger.info("Invitation cleanup handler called (age_days=%d)", age_days)
            # TODO: Implement actual cleanup logic when invitation expiry is added


class RemoveOrphanedAssetsHandler(ScheduledTaskHandler):
    """
    Find and optionally remove assets not linked to any entries.

    Configuration (task_config):
    - age_days: int (default: 30) - Only consider assets older than this
    - auto_delete: bool (default: False) - If true, delete orphans; if false, just log
    - workspace_id: str (optional) - Limit to specific workspace
    """

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        config = task.task_config
        age_days = config.get("age_days", 30)
        auto_delete = config.get("auto_delete", False)
        workspace_id = config.get("workspace_id")

        parsed_workspace_id = UUID(str(workspace_id)) if workspace_id else None

        with session_context() as session:
            repos = AllRepositories(session, group_id=parsed_workspace_id)

            logger.info(
                "Orphaned asset scan: age_days=%d, auto_delete=%s, workspace=%s",
                age_days,
                auto_delete,
                parsed_workspace_id or "all",
            )
            # TODO: Implement actual orphan detection and cleanup


# Register handlers
TaskHandlerRegistry.register("cleanup_temp_files", CleanupTempFilesHandler)
TaskHandlerRegistry.register("prune_expired_sessions", PruneExpiredSessionsHandler)
TaskHandlerRegistry.register("prune_expired_invitations", PruneExpiredInvitationsHandler)
TaskHandlerRegistry.register("remove_orphaned_assets", RemoveOrphanedAssetsHandler)
