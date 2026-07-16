"""
Maintenance task handlers for cleanup and housekeeping.

These handlers perform routine maintenance operations like cleaning up temp files,
pruning old data, and verifying system integrity.
"""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from marvin.core.root_logger import get_logger
from marvin.db.db_setup import session_context
from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel
from marvin.repos.repository_factory import AllRepositories
from marvin.services.event_bus_service.event_bus_service import EventBusService

from . import ScheduledTaskHandler, TaskHandlerRegistry

logger = get_logger(__name__)


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.1f} MB"


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

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> str | None:
        config = task.task_config
        age_hours = config.get("age_hours", 24)
        dry_run = config.get("dry_run", False)

        from marvin.core.config import get_app_dirs
        temp_dir = get_app_dirs().TEMP_DIR

        if not temp_dir.exists():
            msg = f"Temp directory does not exist: {temp_dir}"
            logger.info(msg)
            return msg

        cutoff = datetime.now(UTC) - timedelta(hours=age_hours)
        deleted_count = 0
        deleted_bytes = 0

        for file_path in temp_dir.rglob("*"):
            if not file_path.is_file():
                continue

            mtime = file_path.stat().st_mtime
            file_mtime = datetime.fromtimestamp(mtime, tz=timezone.utc)
            if file_mtime < cutoff:
                file_size = file_path.stat().st_size
                if dry_run:
                    logger.info("Would delete: %s (%s)", file_path, _fmt_bytes(file_size))
                else:
                    file_path.unlink()
                    logger.debug("Deleted: %s (%s)", file_path, _fmt_bytes(file_size))
                deleted_count += 1
                deleted_bytes += file_size

        label = "dry run — would delete" if dry_run else "deleted"
        summary = f"{deleted_count} file{'s' if deleted_count != 1 else ''} {label}, {_fmt_bytes(deleted_bytes)} freed"
        logger.info("Temp file cleanup: %s", summary)
        return summary


class PruneExpiredSessionsHandler(ScheduledTaskHandler):
    """
    Remove expired user sessions from the database.

    Note: Marvin uses JWT tokens — no server-side session storage to prune.
    """

    name = "Prune Expired Sessions"
    description = "Remove expired user sessions (no-op: Marvin uses stateless JWTs)"

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> str | None:
        msg = "No-op: Marvin uses stateless JWT tokens — no session records to prune"
        logger.info(msg)
        return msg


class PruneExpiredInvitationsHandler(ScheduledTaskHandler):
    """
    Remove expired workspace invitations.

    Configuration (task_config):
    - age_days: int (default: 30) - Invitations older than this are deleted
    """

    name = "Prune Expired Invitations"
    description = "Remove workspace invitations older than age_days"
    config_schema = {
        "type": "object",
        "properties": {
            "age_days": {
                "type": "integer",
                "default": 30,
                "description": "Delete invitations older than this many days",
            },
        },
    }

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> str | None:
        from marvin.db.models.users.invitations import GroupInviteModel

        config = task.task_config
        age_days = config.get("age_days", 30)
        cutoff = datetime.now(UTC) - timedelta(days=age_days)

        with session_context() as session:
            expired = (
                session.query(GroupInviteModel)
                .filter(GroupInviteModel.created_at <= cutoff)
                .all()
            )
            count = len(expired)
            for inv in expired:
                session.delete(inv)
            session.commit()

        summary = f"{count} expired invitation{'s' if count != 1 else ''} deleted (older than {age_days} days)"
        logger.info("Invitation cleanup: %s", summary)
        return summary


class RemoveOrphanedAssetsHandler(ScheduledTaskHandler):
    """
    Find and optionally remove assets not linked to any entries.

    Configuration (task_config):
    - age_days: int (default: 30) - Only consider assets older than this
    - auto_delete: bool (default: False) - If true, delete orphans; if false, just report
    - workspace_id: str (optional) - Limit to specific workspace
    """

    name = "Remove Orphaned Assets"
    description = "Find (and optionally delete) assets not linked to any entries"
    config_schema = {
        "type": "object",
        "properties": {
            "age_days": {
                "type": "integer",
                "default": 30,
                "description": "Only consider assets older than this many days",
            },
            "auto_delete": {
                "type": "boolean",
                "default": False,
                "description": "If true, delete orphans; if false, just report",
            },
            "workspace_id": {
                "type": "string",
                "description": "Limit scan to this workspace UUID (omit for all workspaces)",
            },
        },
    }

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> str | None:
        from marvin.db.models.platform import Assets, EntryAssets

        config = task.task_config
        age_days = config.get("age_days", 30)
        auto_delete = config.get("auto_delete", False)
        workspace_id_raw = config.get("workspace_id")
        workspace_id = UUID(str(workspace_id_raw)) if workspace_id_raw else None

        cutoff = datetime.now(UTC) - timedelta(days=age_days)

        with session_context() as session:
            q = session.query(Assets).filter(Assets.created_at <= cutoff)
            if workspace_id:
                q = q.filter(Assets.group_id == workspace_id)

            all_assets = q.all()

            linked_ids = {
                row[0]
                for row in session.query(EntryAssets.asset_id).all()
            }

            orphans = [a for a in all_assets if a.id not in linked_ids]
            count = len(orphans)

            if auto_delete:
                for asset in orphans:
                    session.delete(asset)
                session.commit()
                label = "deleted"
            else:
                label = "found (auto_delete=false, not removed)"

        scope = str(workspace_id) if workspace_id else "all workspaces"
        summary = (
            f"{count} orphaned asset{'s' if count != 1 else ''} {label} "
            f"(older than {age_days} days, scope: {scope})"
        )
        logger.info("Orphaned asset scan: %s", summary)
        return summary


# Register handlers
TaskHandlerRegistry.register("cleanup_temp_files", CleanupTempFilesHandler)
TaskHandlerRegistry.register("prune_expired_sessions", PruneExpiredSessionsHandler)
TaskHandlerRegistry.register("prune_expired_invitations", PruneExpiredInvitationsHandler)
TaskHandlerRegistry.register("remove_orphaned_assets", RemoveOrphanedAssetsHandler)
